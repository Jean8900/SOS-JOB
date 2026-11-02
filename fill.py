"""Programme local du pré-remplissage de formulaires : Ctrl+Alt+Espace dans Chrome ou Edge.

Tourne en tâche de fond (voir `.\\fill.ps1 install` pour le lancer à l'ouverture de session) :
- écoute le raccourci global ; si la fenêtre active est Chrome ou Edge, envoie l'ordre à l'extension
  de CE navigateur (dossier extension/, installée une fois dans Chrome et dans Edge) ;
- l'extension lit les champs vides de la page et les envoie ici ; on fait rédiger les réponses par
  Claude (CV + input/form_profile.yaml + page) ; l'extension les écrit dans les champs.
Rien n'est envoyé : tu relis puis tu valides toi-même. Le serveur n'écoute que sur 127.0.0.1 et
n'accepte que les requêtes de l'extension (en-tête dédié + origine chrome-extension://).

Usage : python fill.py   (Ctrl+C pour arrêter)
"""
from __future__ import annotations

import base64
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import config, formfill, winlayout  # noqa: E402
from src.hotkeys import HotkeyListener  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent
LOG_PATH = REPO_ROOT / "output" / "copilot" / "fill.log"
BROWSERS = {"chrome.exe": "chrome", "msedge.exe": "edge"}
POLL_SECONDS = 20
EXTENSION_ALIVE_SECONDS = 45  # l'extension re-sollicite le serveur au moins toutes les ~30 s

# Un ordre par type de navigateur (numéro + heure). Chaque instance d'extension (deux profils Chrome = deux
# instances) le reçoit une fois, tant qu'il a moins de ORDER_TTL secondes : une instance qui se connecte juste
# après l'appui du raccourci le reçoit aussi. Seule celle dont la fenêtre a le focus l'exécute (background.js).
ORDER_TTL = 20
orders: dict[str, dict] = {"chrome": {"seq": 0, "ts": 0.0}, "edge": {"seq": 0, "ts": 0.0}}
delivered: dict[str, int] = {}  # instance -> dernier ordre reçu
order_changed = threading.Condition()
instance_seen: dict[str, float] = {}
instance_browser: dict[str, str] = {}
last_seen: dict[str, float] = {"chrome": 0.0, "edge": 0.0}
busy_since: dict[str, float] = {"chrome": 0.0, "edge": 0.0}  # 0 = libre ; un ordre sans réponse expire après 2 min
last_note: dict[str, str] = {"chrome": "", "edge": ""}  # compte rendu du dernier remplissage (lu par batch.py via /result)


REPORTS_DIR = REPO_ROOT / "output" / "copilot" / "reports"
SHOTS_DIR = REPO_ROOT / "output" / "copilot" / "shots"
TRACE_PATH = REPO_ROOT / "output" / "copilot" / "trace.log"
KEEP = 3  # rapports et captures gardés par offre (pour comparer avant / après une correction)
last_report: dict[str, dict] = {}


def offer_key(url: str) -> str:
    """Clé d'offre lisible : hôte + fin du chemin, sans paramètres ni valeur perso."""
    parts = urlparse(url)
    tail = "-".join(p for p in parts.path.split("/") if p)[-48:]
    return re.sub(r"[^A-Za-z0-9._-]+", "_", f"{parts.hostname or 'web'}_{tail}")[:90]


def prune(folder: Path, key: str, suffix: str) -> None:
    files = sorted(folder.glob(f"{key}__*{suffix}"))
    for old in files[:-KEEP]:
        old.unlink(missing_ok=True)


def save_report(browser: str, rep: dict) -> None:
    """Rapport structuré d'un remplissage : fichier JSON (3 derniers par offre) + lignes de trace.log."""
    key = offer_key(rep.get("url", ""))
    stamp = time.strftime("%Y%m%d-%H%M%S")
    rep["ts"] = time.time()
    rep["key"] = key
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / f"{key}__{stamp}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    prune(REPORTS_DIR, key, ".json")
    last_report[browser] = rep
    lines = [f"{time.strftime('%H:%M:%S')} {key}"]
    for st in rep.get("steps", []):
        lines.append(f"  étape {st.get('n')} : champs={st.get('filled', 0)} fichiers={st.get('uploaded', 0)} clic={st.get('clicked') or '-'} avancé={st.get('moved', '-')}")
    for err in rep.get("errors", []):
        lines.append(f"  ERREUR étape {err.get('step')} [{err.get('kind')}] {err.get('where')} : {err.get('msg')}")
    for crit in (rep.get("state") or {}).get("criteria", []):
        lines.append(f"  {'OK ' if crit.get('ok') else 'KO '} {crit.get('k')} {crit.get('v', '')}")
    stop = rep.get("stop") or {}
    lines.append(f"  arrêt [{stop.get('code')}] {stop.get('text')}")
    if rep.get("shot"):
        lines.append(f"  capture {rep['shot']}")
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRACE_PATH.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def save_shot(url: str, data_url: str) -> str:
    key = offer_key(url)
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SHOTS_DIR / f"{key}__{time.strftime('%Y%m%d-%H%M%S')}.png"
    path.write_bytes(base64.b64decode(data_url.split(",", 1)[-1]))
    prune(SHOTS_DIR, key, ".png")
    return str(path.relative_to(REPO_ROOT))


def log(message: str) -> None:
    print(time.strftime("%H:%M:%S"), message, flush=True)


class QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address) -> None:  # connexion coupée par le navigateur : sans importance
        pass


def make_handler(cfg: dict, port: int):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # pas de journal HTTP
            pass

        def _allowed(self) -> bool:
            # Une page web ne peut pas joindre ce serveur : son Origin n'est pas celui d'une extension, et
            # l'en-tête X-SOSJOB (vérifié aussi ailleurs) exige une vérification préalable (OPTIONS) qu'on lui refuse.
            origin = self.headers.get("Origin", "")
            return (self.headers.get("Host", "") in (f"127.0.0.1:{port}", f"localhost:{port}")
                    and (not origin or origin.startswith("chrome-extension://")))

        def _send(self, status: int, body: dict | None = None) -> None:
            data = json.dumps(body or {}).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", ""))
            self.send_header("Access-Control-Allow-Headers", "X-SOSJOB, Content-Type")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self) -> None:  # préflight : seulement pour une extension
            self._send(204) if self._allowed() else self._send(403)

        def do_GET(self) -> None:
            if not self._allowed() or self.headers.get("X-SOSJOB") != "1":
                return self._send(403)
            url = urlparse(self.path)
            query = parse_qs(url.query)
            browser = (query.get("b") or [""])[0]
            instance = (query.get("i") or ["?"])[0][:40]
            if browser not in orders:
                return self._send(400)
            last_seen[browser] = time.time()
            if url.path == "/poll":
                # Instance jamais vue : elle ne reçoit pas les ordres d'avant sa connexion (pas d'écho d'un ordre
                # déjà exécuté ailleurs). Une instance connue qui se réveille reçoit l'ordre en attente.
                if instance not in delivered:
                    delivered[instance] = orders[browser]["seq"]
                instance_browser[instance] = browser
                cmd, previous = None, delivered[instance]
                deadline = time.time() + POLL_SECONDS
                with order_changed:
                    while True:
                        order = orders[browser]
                        if order["seq"] > previous and time.time() - order["ts"] < ORDER_TTL:
                            delivered[instance] = order["seq"]
                            cmd = "fill"
                            break
                        if time.time() >= deadline:
                            break
                        order_changed.wait(timeout=deadline - time.time())
                last_seen[browser] = instance_seen[instance] = time.time()
                try:
                    return self._send(200, {"cmd": cmd})
                except OSError:  # client parti (navigateur fermé) : l'ordre n'a pas été livré, une autre instance le recevra
                    if cmd:
                        delivered[instance] = previous
                    return None
            if url.path == "/status":  # pour le banc d'essai : instances d'extension vues récemment (âge en secondes)
                now = time.time()
                return self._send(200, {"instances": {i: round(now - seen, 1) for i, seen in instance_seen.items()
                                                       if instance_browser.get(i) == browser and now - seen < EXTENSION_ALIVE_SECONDS}})
            if url.path == "/done":
                note = (query.get("note") or [""])[0]
                if note:
                    log(f"  extension ({instance[:4]}) : {note}")
                if not note.startswith("ordre ignoré"):  # une instance sans focus ne libère pas l'ordre de celle qui travaille
                    last_note[browser] = note or "terminé"
                    busy_since[browser] = 0.0
                return self._send(200)
            if url.path == "/trigger":  # remplacement du raccourci pour batch.py (processus local, sans en-tête Origin)
                return self._send(200, {"started": request_fill(browser)})
            if url.path == "/result":  # batch.py : le remplissage demandé est-il terminé ?
                return self._send(200, {"busy": busy_since[browser] > 0 and time.time() - busy_since[browser] < 600,
                                        "note": last_note[browser]})
            if url.path == "/file":  # CV / LM de l'offre en cours (copiés par apply.py ou batch.py dans le dossier d'upload)
                kind = (query.get("k") or [""])[0]
                log(f"  /file {kind}")
                names = {"cv": "CV_{}.pdf", "lm": "LM_{}.pdf", "lmtxt": "LM_{}.txt"}
                if kind not in names:
                    return self._send(404)
                path = REPO_ROOT / cfg["staging_dir"] / names[kind].format(cfg["file_name"])
                if not path.is_file():
                    return self._send(404)
                data = path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8" if kind == "lmtxt" else "application/pdf")
                self.send_header("Access-Control-Allow-Origin", self.headers.get("Origin", ""))
                self.send_header("Access-Control-Expose-Headers", "X-Filename")
                self.send_header("X-Filename", path.name)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return None
            if url.path == "/report":  # batch.py --debug : dernier rapport de remplissage
                return self._send(200, {"report": last_report.get(browser)})
            self._send(404)

        def do_POST(self) -> None:
            url = urlparse(self.path)
            if not self._allowed() or self.headers.get("X-SOSJOB") != "1" or url.path not in ("/answers", "/report", "/shot"):
                return self._send(403)
            browser = (parse_qs(url.query).get("b") or ["chrome"])[0]
            try:
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                if url.path == "/report":
                    save_report(browser if browser in orders else "chrome", payload)
                    return self._send(200, {"ok": True})
                if url.path == "/shot":
                    return self._send(200, {"path": save_shot(payload.get("url", ""), payload["png"])})
                if formfill.is_excluded(payload["url"], cfg):
                    return self._send(200, {"excluded": formfill.urlparse(payload["url"]).hostname})
                fields = payload["fields"]
                offer = formfill.offer_from_context(payload["url"], payload.get("title", ""), payload.get("text", ""))
                started = time.time()
                letter = formfill.staged_letter(cfg)
                answers = formfill.generate_answers(offer, fields, cfg, letter=letter)
                answers = formfill.complete_answers(offer, fields, answers, cfg, letter=letter)
                final, short = formfill.finalize_answers(fields, answers)
                log(f"{len(final)}/{len(fields)} réponse(s) en {time.time() - started:.0f}s pour {formfill.urlparse(payload['url']).hostname}")
                self._send(200, {"answers": final, "short": short})
            except Exception as exc:  # un échec ne doit jamais arrêter le serveur
                log(f"échec : {exc}")
                self._send(200, {"error": str(exc)[:160]})

    return Handler


def on_hotkey() -> None:
    hwnd = winlayout.foreground_window()
    browser = BROWSERS.get(winlayout.window_process_name(hwnd))
    if browser is None:
        log("raccourci ignoré : la fenêtre active n'est ni Chrome ni Edge")
        return
    request_fill(browser)


def request_fill(browser: str) -> bool:
    """Envoie l'ordre de remplissage aux extensions de ce navigateur. False si un remplissage est déjà en cours."""
    if time.time() - busy_since[browser] < 120:
        return False
    busy_since[browser] = time.time()
    last_note[browser] = ""
    alive = sum(1 for seen in instance_seen.values() if time.time() - seen < EXTENSION_ALIVE_SECONDS)
    with order_changed:
        orders[browser]["seq"] += 1
        orders[browser]["ts"] = time.time()
        order_changed.notify_all()
    log(f"remplissage demandé dans {browser} ({alive} instance(s) d'extension à l'écoute)")
    if not alive:
        log("  aucune extension à l'écoute pour l'instant : l'ordre reste valable 30 s (extension installée ? voir extension/README.md)")
    return True


def main() -> None:
    if sys.stdout is None or sys.stderr is None:  # pythonw (démarrage automatique) : pas de console
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        sys.stdout = sys.stderr = open(LOG_PATH, "a", encoding="utf-8", buffering=1)
    cfg = config.load_copilot()
    port = int(cfg.get("fill_server_port", 47321))
    try:
        server = QuietServer(("127.0.0.1", port), make_handler(cfg, port))
    except OSError:
        log(f"déjà lancé (port {port} occupé) : rien à faire")
        return
    threading.Thread(target=server.serve_forever, daemon=True).start()

    hotkeys = HotkeyListener({"fill": 0x20})  # Ctrl+Alt+Espace (Ctrl+Alt+Q reste « quitter » dans apply.ps1)
    hotkeys.start()
    if hotkeys.failed:
        log("Ctrl+Alt+Espace est déjà pris par une autre application")
        return
    log(f"prêt : Ctrl+Alt+Espace dans Chrome / Edge, extension sur 127.0.0.1:{port}")
    try:
        while True:
            hotkeys.wait()
            on_hotkey()
    except KeyboardInterrupt:
        pass
    finally:
        hotkeys.stop()
        server.shutdown()


if __name__ == "__main__":
    main()
