"""Candidature de bout en bout depuis un formulaire local (src/go.html, à ouvrir dans VS Code : Simple Browser).

Le formulaire donne les critères, les sites et le nombre d'offres. 1re validation : ouvre les sites à connexion dans
Chrome. 2e validation : un fil collecte et génère CV + LM site par site, un autre remplit les offres du site dont la
génération est finie (la génération garde donc un site d'avance). Rien n'est envoyé : l'extension s'arrête avant
le bouton d'envoi, tu relis et tu cliques toi-même dans chaque onglet.

Usage : python go.py [--record]   (ou .\\go.ps1 ; Ctrl+C pour arrêter)
  --record : filme l'écran du 2e Entrée jusqu'au message de fin (output/demo/<horodatage>/go.mp4). Les connexions ne sont
             pas filmées, mais les formulaires remplis le sont : relis la vidéo avant de la partager.
"""
from __future__ import annotations

import argparse
import importlib
import json
import queue
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import alertes  # noqa: E402
from apply import _find_chrome, apply_url  # noqa: E402
from batch import LOGIN_SITES, call, ensure_pdfs, fill_offer, open_in_chrome, reset_attempts  # noqa: E402
from src import applications, config, gmail, matcher, winlayout  # noqa: E402
from src.recorder import PausableRecorder, find_ffmpeg  # noqa: E402
from src.offer import Offer  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent
PAGE = REPO_ROOT / "src" / "go.html"
FORM_PATH = REPO_ROOT / "output" / "copilot" / "go_form.json"
EXTENSION_WAIT = 35  # secondes : l'extension re-sollicite le programme local au moins toutes les ~30 s
FORM_TITLE = "SOS-JOB Go"
FINAL_SECONDS = 6  # le message de fin reste à l'écran avant la fin de la vidéo
DONE_TEXT = "c'est fait bro 😎 mtn à toi de clicker pour submit toutes les {n} offres candidatées"

lock = threading.Lock()
apps_lock = threading.Lock()  # applications.json : lu puis réécrit par les deux fils
resume = threading.Event()
state: dict = {"phase": "idle", "opened": [], "mail": {"status": "loading", "error": "", "sites": {}},
               "gen_msg": "", "fill_msg": "", "percent": 0, "fill_percent": 0, "log": [], "error": "", "done": "", "waiting": 0, "video": ""}
mail_offers: dict[str, list[dict]] = {}
progress: dict = {}
ffmpeg_path: str | None = None  # renseigné par --record
film: PausableRecorder | None = None


def update(**values) -> None:
    with lock:
        state.update(values)


def log(line: str) -> None:
    print(line, flush=True)
    with lock:
        state["log"].append(line)


def catalog() -> dict:
    """Sites proposés par le formulaire (input/sites.yaml) et valeurs de départ (dernier formulaire, sinon criteria.yaml)."""
    cfg = config.load_sites()
    sites = [{"slug": s["slug"], "name": s["name"], "login_url": s.get("login_url", ""), "enabled": bool(s.get("enabled"))} for s in cfg["sites"]]
    criteria = config.load_criteria()
    form = {"filter": not criteria.get("disable_filters"), "professions": list(criteria.get("professions") or []),
            "years_min": criteria.get("years_min"), "years_max": criteria.get("years_max"),
            "n": int(cfg.get("max_results_per_site", 5)), "dedicated": False,
            "sites": {s["slug"]: {"on": s["enabled"], "n": None} for s in sites},
            "mail": {m["slug"]: None for m in cfg.get("mail_sites", [])}}
    try:
        saved = json.loads(FORM_PATH.read_text(encoding="utf-8"))
        form.update({k: v for k, v in saved.items() if k not in ("sites", "mail")})
        form["sites"].update({k: v for k, v in saved.get("sites", {}).items() if k in form["sites"]})
        form["mail"].update({k: v for k, v in saved.get("mail", {}).items() if k in form["mail"]})
    except (OSError, ValueError):
        pass
    return {"sites": sites, "mail_sites": cfg.get("mail_sites", []), "form": form,
            "locations": criteria.get("locations") or [], "contract_types": criteria.get("contract_types") or []}


def _count(value) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def plan_from(form: dict) -> list[dict]:
    """Sites à traiter et nombre d'offres de chacun. Mode dédié ou site d'alertes : case vide = pas de candidature."""
    cfg = config.load_sites()
    plan = []
    for site in cfg["sites"]:
        choice = form.get("sites", {}).get(site["slug"]) or {}
        n = _count(choice.get("n")) if form.get("dedicated") else _count(form.get("n"))
        if choice.get("on") and n:
            plan.append({"slug": site["slug"], "name": site["name"], "login_url": site.get("login_url", ""), "n": n, "mail": False})
    with lock:
        available = {slug: info["new"] for slug, info in state["mail"]["sites"].items()}
    for site in cfg.get("mail_sites", []):
        n = min(_count(form.get("mail", {}).get(site["slug"])), available.get(site["slug"], 0))
        if n:
            plan.append({"slug": site["slug"], "name": site["name"], "login_url": "", "n": n, "mail": True})
    return plan


def is_new(offer: Offer, known: dict[str, str]) -> bool:
    return known.get(applications.offer_key(offer), applications.PENDING) == applications.PENDING


def _mail_offer(raw: dict) -> Offer:
    return Offer(source=raw["source"], source_id=raw["source_id"], url=raw["url"], url_canonique=raw["url"], title=raw["title"],
                 company=raw["company"], location=raw["location"], description=raw["description"])


def read_mails() -> None:
    """Lit les alertes au démarrage pour afficher tout de suite le nombre d'offres reçues (lecture seule, sans fenêtre)."""
    wanted = [m["slug"] for m in config.load_sites().get("mail_sites", [])]
    try:
        lot = alertes.collect(int(config.load_copilot().get("go_alert_days", 3)), wanted, interactive=False)
    except gmail.GmailError as exc:
        with lock:
            state["mail"] = {"status": "error", "error": str(exc), "sites": {}}
        return
    except Exception as exc:  # noqa: BLE001 -- sans Gmail, le reste du formulaire doit marcher
        with lock:
            state["mail"] = {"status": "error", "error": f"{type(exc).__name__} : {exc}", "sites": {}}
        return
    with apps_lock:
        known = applications.statuses()
    sites = {}
    for slug in wanted:
        mail_offers[slug] = [o for o in lot if o["source"] == slug]
        sites[slug] = {"received": len(mail_offers[slug]), "new": sum(is_new(_mail_offer(o), known) for o in mail_offers[slug])}
    with lock:
        state["mail"] = {"status": "ready", "error": "", "sites": sites}


def recount_mails() -> None:
    with apps_lock:
        known = applications.statuses()
    with lock:
        for slug, info in state["mail"]["sites"].items():
            info["new"] = sum(is_new(_mail_offer(o), known) for o in mail_offers.get(slug, []))


def collect(site: dict) -> list[Offer]:
    """Offres du site qui passent le filtre et ne sont pas déjà traitées, au plus site["n"]."""
    criteria = config.load_criteria()
    if site["mail"]:  # une alerte ne donne que le titre : seuls le métier et l'expérience sont testables
        found = [_mail_offer(o) for o in mail_offers.get(site["slug"], [])]
        criteria = {**criteria, "locations": [], "contract_types": [], "stack": []}
    else:
        factor = int(config.load_copilot().get("go_collect_factor", 4))
        found = importlib.import_module(f"src.connectors.{site['slug']}").fetch(max_results=site["n"] * factor)
    with apps_lock:
        known = applications.statuses()
    return [o for o in matcher.filter_offers(found, criteria) if is_new(o, known)][:site["n"]]


def refresh_percent() -> None:
    total = sum(s["target"] for s in progress.values()) or 1
    generated = sum(s["generated"] for s in progress.values())
    attempted = sum(s["attempted"] for s in progress.values())
    update(percent=round(100 * (generated + attempted) / (2 * total)), fill_percent=round(100 * attempted / total))


def generate_all(plan: list[dict], ready: queue.Queue) -> None:
    """Collecte et génère site par site. Un site ou une offre en échec n'arrête jamais les autres."""
    for i, site in enumerate(plan, start=1):
        slug = site["slug"]
        update(gen_msg=f"Collecte des offres site {i}/{len(plan)} ({site['name']})")
        try:
            offers = collect(site)
        except Exception as exc:  # noqa: BLE001
            log(f"[{site['name']}] collecte en échec : {exc}")
            offers = []
        progress[slug]["target"] = len(offers)
        if len(offers) < site["n"]:
            log(f"[{site['name']}] {len(offers)}/{site['n']} offre(s) retenue(s) après filtre (marge : go_collect_factor dans input/copilot.yaml)")
        refresh_percent()
        done = []
        for j, offer in enumerate(offers, start=1):
            update(gen_msg=f"Génération CV / LM site {i}/{len(plan)} ({site['name']}) : offre {j}/{len(offers)}")
            try:
                ensure_pdfs(offer)
                with apps_lock:
                    applications.register([offer])
                done.append(offer)
                progress[slug]["generated"] += 1
            except Exception as exc:  # noqa: BLE001
                log(f"[{site['name']}] {offer.title[:50]} : CV/LM en échec : {exc}")
                progress[slug]["target"] -= 1
            refresh_percent()
        ready.put((site, done))
    update(gen_msg="Génération terminée")
    ready.put(None)


def is_ready(rep: dict | None) -> bool:
    """Formulaire prêt à envoyer : tous les critères de l'extension sont bons et la candidature est bien sur ce site."""
    criteria = ((rep or {}).get("state") or {}).get("criteria") or []
    return bool(criteria) and all(c.get("ok") or c.get("skip") for c in criteria) and not any(c.get("k") == "hors_site" for c in criteria)


def worked(rep: dict | None) -> bool:
    """Le remplissage a-t-il écrit quelque chose ? Sinon l'offre reste en attente et pourra être reprise."""
    return is_ready(rep) or any(step.get("filled") or step.get("uploaded") for step in (rep or {}).get("steps", []))


def fill_all(ready: queue.Queue, port: int) -> tuple[int, int]:
    """Remplit les offres dès que leur site est généré. Retourne (prêtes à envoyer, à finir à la main)."""
    cfg = config.load_copilot()
    staging = REPO_ROOT / cfg["staging_dir"]
    staging.mkdir(parents=True, exist_ok=True)
    profile = (yaml.safe_load(LOGIN_SITES.read_text(encoding="utf-8")) or {}).get("profile_directory", "") if LOGIN_SITES.exists() else ""
    chrome = _find_chrome()
    counts = {"ready": 0, "manual": 0}
    waiting: list[tuple[dict, Offer, dict]] = []

    def process(site: dict, offer: Offer, entry: dict) -> None:
        rep = fill_offer(offer, entry, port, chrome, profile, staging, cfg["file_name"])
        if entry["login_needed"]:
            return
        with apps_lock:
            if entry["ran"] and worked(rep):
                applications.set_status(applications.offer_key(offer), applications.FILLED)
        counts["ready" if is_ready(rep) else "manual"] += 1
        log(f"[{site['name']}] {offer.title[:50]} -> {'prête à envoyer' if is_ready(rep) else entry.get('note', '')[:140]}")

    while (item := ready.get()) is not None:
        site, offers = item
        for j, offer in enumerate(offers, start=1):
            update(fill_msg=f"Remplissage {site['name']} : offre {j}/{len(offers)}")
            entry = {"key": applications.offer_key(offer), "source": offer.source, "title": offer.title, "company": offer.company, "url": apply_url(offer)}
            try:
                process(site, offer, entry)
                if entry["login_needed"]:
                    waiting.append((site, offer, entry))
                    log(f"[{site['name']}] {offer.title[:50]} -> connexion demandée, reprise à la fin")
            except Exception as exc:  # noqa: BLE001
                counts["manual"] += 1
                log(f"[{site['name']}] {offer.title[:50]} : remplissage en échec : {exc}")
            progress[site["slug"]]["attempted"] += 1
            refresh_percent()
        update(fill_msg="En attente de la génération du site suivant")

    if waiting:
        resume.clear()
        if film:
            film.pause()  # une connexion n'est jamais filmée
        update(phase="login", waiting=len(waiting), fill_msg=f"{len(waiting)} offre(s) demandent une connexion : connecte-toi dans leurs onglets, puis Reprendre")
        resume.wait()
        update(phase="running", waiting=0)
        if film and state.get("resume_choice") == "retry":
            film.start()
        if state.get("resume_choice") == "retry":
            for k, (site, offer, entry) in enumerate(waiting, start=1):
                update(fill_msg=f"Reprise après connexion : offre {k}/{len(waiting)}")
                try:
                    process(site, offer, entry)
                    if entry["login_needed"]:
                        counts["manual"] += 1
                        log(f"[{site['name']}] {offer.title[:50]} -> toujours pas connecté")
                except Exception as exc:  # noqa: BLE001
                    counts["manual"] += 1
                    log(f"[{site['name']}] {offer.title[:50]} : remplissage en échec : {exc}")
        else:
            counts["manual"] += len(waiting)
    return counts["ready"], counts["manual"]


def ensure_fill_program(port: int) -> None:
    """Lance le programme local s'il ne tourne pas, puis attend que l'extension de Chrome se manifeste."""
    try:
        call(port, "/result", "chrome")
    except OSError:
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        subprocess.Popen([str(pythonw if pythonw.exists() else sys.executable), str(REPO_ROOT / "fill.py")], cwd=REPO_ROOT,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(3)
    deadline = time.time() + EXTENSION_WAIT
    while time.time() < deadline:
        try:
            if call(port, "/status", "chrome").get("instances"):
                return
        except OSError:
            pass
        time.sleep(2)
    raise RuntimeError("extension non détectée dans Chrome : vérifie chrome://extensions (voir extension/README.md), puis relance")


def show_form() -> None:
    """Remet le formulaire à l'écran : sa fenêtre si elle porte son titre, sinon VS Code (Simple Browser)."""
    hwnd = winlayout.find_window("Chrome_WidgetWin_1", FORM_TITLE, timeout=1) or winlayout.process_window("code.exe")
    if hwnd:
        winlayout.bring_to_front(hwnd)


def start_film() -> None:
    global film
    if not ffmpeg_path:
        return
    run_dir = REPO_ROOT / "output" / "demo" / time.strftime("%Y-%m-%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    film = PausableRecorder(ffmpeg_path, run_dir / "go.mp4", int(config.load_copilot().get("go_video_fps", 15)))
    film.start()
    time.sleep(2)  # la vidéo s'ouvre sur le formulaire


def finish_film() -> None:
    global film
    if not film:
        return
    current, film = film, None
    if current.current:  # déjà en pause (arrêt pendant une reconnexion) : pas de nouvelle image
        show_form()
        time.sleep(FINAL_SECONDS)
    video = current.finish()
    update(video=str(video) if video else "")
    log(f"Vidéo : {video}" if video else "Vidéo : aucun fichier produit")


def run(plan: list[dict]) -> None:
    try:
        start_film()
        update(gen_msg="Vérification du programme local et de l'extension")
        port = int(config.load_copilot().get("fill_server_port", 47321))
        ensure_fill_program(port)
        ready: queue.Queue = queue.Queue(maxsize=1)  # la génération garde de l'avance sans courir loin devant le remplissage
        threading.Thread(target=generate_all, args=(plan, ready), daemon=True).start()
        n_ready, n_manual = fill_all(ready, port)
        text = DONE_TEXT.format(n=n_ready)
        if n_manual:
            text += f" ({n_manual} autre(s) à finir à la main, voir le journal)"
        update(phase="done", done=text, percent=100, fill_percent=100, gen_msg="", fill_msg="")
    except Exception as exc:  # noqa: BLE001 -- l'erreur s'affiche sur le formulaire au lieu de le figer
        log(f"Arrêt : {exc}")
        update(phase="error", error=str(exc), gen_msg="", fill_msg="")
    finally:
        finish_film()


def save_form(form: dict) -> None:
    FORM_PATH.parent.mkdir(parents=True, exist_ok=True)
    FORM_PATH.write_text(json.dumps(form, ensure_ascii=False, indent=1), encoding="utf-8")


def apply_criteria(form: dict) -> None:
    def year(value):
        return _count(value) if value not in (None, "") else None
    # La pile technique n'est pas dans le formulaire : elle n'écarte rien ici. Lieux et contrats non plus : le formulaire ne les
    # propose pas, donc go ne garde que les critères qu'il affiche (ceux de criteria.yaml ne s'appliquent pas à un go).
    config.set_criteria_override({"disable_filters": not form.get("filter"), "stack": [], "locations": [], "contract_types": [],
                                  "integrated_apply_only": True, "professions": [p for p in form.get("professions", []) if p.strip()],
                                  "years_min": year(form.get("years_min")), "years_max": year(form.get("years_max"))})


def connect(form: dict) -> dict:
    """Ouvre dans Chrome, chacun dans un onglet, les sites choisis où il faut se connecter et pas encore ouverts."""
    save_form(form)
    with lock:
        opened = list(state["opened"])
    todo = [s for s in plan_from(form) if s["login_url"] and s["slug"] not in opened]
    profile = (yaml.safe_load(LOGIN_SITES.read_text(encoding="utf-8")) or {}).get("profile_directory", "") if LOGIN_SITES.exists() else ""
    chrome = _find_chrome()
    for site in todo:
        open_in_chrome(chrome, site["login_url"], profile)
        opened.append(site["slug"])
    update(opened=opened)
    return {"ok": True}


def start(form: dict) -> dict:
    save_form(form)
    plan = plan_from(form)
    if not plan:
        return {"ok": False, "error": "Choisis au moins un site et un nombre d'offres."}
    with lock:
        if state["phase"] in ("running", "login"):
            return {"ok": False, "error": "Déjà en cours."}
        state.update(phase="running", log=[], error="", done="", video="", percent=0, fill_percent=0, gen_msg="", fill_msg="")
    apply_criteria(form)
    reset_attempts()  # la règle des 30 tentatives s'applique par run
    progress.clear()
    progress.update({s["slug"]: {"target": s["n"], "generated": 0, "attempted": 0} for s in plan})
    threading.Thread(target=run, args=(plan,), daemon=True).start()
    return {"ok": True}


def reset() -> dict:
    recount_mails()
    with lock:
        if state["phase"] not in ("done", "error"):
            return {"ok": False}
        state.update(phase="idle", log=[], error="", done="", video="", percent=0, fill_percent=0, gen_msg="", fill_msg="")
    return {"ok": True}


def make_handler(port: int):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_) -> None:
            pass

        def _send(self, code: int, body: bytes, content_type: str = "application/json; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, payload: dict, code: int = 200) -> None:
            self._send(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"))

        def do_GET(self) -> None:
            if self.headers.get("Host") not in allowed_hosts:  # une page web ne peut pas viser ce serveur via un autre nom d'hôte
                return self._json({"error": "hôte refusé"}, 403)
            if self.path == "/":
                return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if self.path == "/catalog":
                return self._json(catalog())
            if self.path == "/state":
                with lock:
                    return self._json(state)
            self._json({"error": "introuvable"}, 404)

        def do_POST(self) -> None:
            # L'en-tête dédié impose un préflight CORS, jamais accordé : une page web ne peut rien déclencher ici.
            if self.headers.get("Host") not in allowed_hosts or self.headers.get("X-SOSJOB-GO") != "1":
                return self._json({"error": "requête refusée"}, 403)
            length = int(self.headers.get("Content-Length") or 0)
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/connect":
                    return self._json(connect(body))
                if self.path == "/start":
                    return self._json(start(body))
                if self.path == "/reset":
                    return self._json(reset())
                if self.path == "/resume":
                    update(resume_choice="retry" if body.get("retry") else "drop")
                    resume.set()
                    return self._json({"ok": True})
                self._json({"error": "introuvable"}, 404)
            except Exception as exc:  # noqa: BLE001 -- une erreur s'affiche sur le formulaire
                self._json({"ok": False, "error": str(exc)})

    return Handler


def main() -> None:
    global ffmpeg_path
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", action="store_true", help="filme l'écran du 2e Entrée jusqu'au message de fin")
    if parser.parse_args().record:
        ffmpeg_path = find_ffmpeg()
        if not ffmpeg_path:
            raise SystemExit("ffmpeg introuvable (winget install Gyan.FFmpeg)")
    port = int(config.load_copilot().get("go_port", 47322))
    url = f"http://127.0.0.1:{port}/"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(port))
    except OSError:
        print(f"Déjà lancé : {url}")
        return
    threading.Thread(target=read_mails, daemon=True).start()
    subprocess.run("clip", input=url.encode("ascii"), check=False)
    print(f"Formulaire : {url} (adresse copiée)")
    print("Dans VS Code : Ctrl+Shift+P > « Simple Browser: Show » > Ctrl+V > Entrée. Ctrl+C ici pour arrêter.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
