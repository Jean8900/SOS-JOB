"""Démo filmée et test de non-régression (TNR) de la chaîne complète, dans TON Chrome (sites déjà connectés via .\\login.ps1).

  0. vérifications : programme local de remplissage, jeton Gmail, ffmpeg, Chrome
  1. alertes email (Gmail, lecture seule) -> lot d'offres Apec / HelloWork (affiché, pas candidaté en V1)
  2. offres WTJ « Software Engineer » à candidature intégrée, CV et LM générés une par une
  3. remplissage jusqu'avant l'envoi (jamais cliqué) : 3 offres réussies visées, 3 essais max par offre,
     20 essais max au total ; une offre qui sort de WTJ est abandonnée tout de suite ; onglets ratés refermés
  4. diaporama des onglets réussis, puis verdict par offre

Tout l'écran est filmé par ffmpeg : output/demo/<horodatage>/demo.mp4 (+ rapport.json, rapport.md).
Code de sortie 0 si l'objectif est atteint (TNR vert), 1 sinon. Ne touche ni au clavier ni à la souris pendant la démo.

Usage : python demo.py [-n 3] [--query "Software Engineer"] [--no-video] [--fps 15]
"""
from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import alertes  # noqa: E402
import wtj_prepare  # noqa: E402
from apply import _find_chrome, apply_url, stage_files  # noqa: E402
from batch import LOGIN_SITES, call, fetch_report, focus_chrome, run_one, site_attempts, MAX_SITE_ATTEMPTS  # noqa: E402
from src import config, gmail, winlayout  # noqa: E402
from src.recorder import Recorder, find_ffmpeg  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent
OK_STOPS = {"review", "submit_ready", "no_button"}  # mêmes codes « arrivé au bout » que l'extension
MAX_TRIES_PER_OFFER = 3
MAX_TRIES_TOTAL = 20
SLIDE_SECONDS = 6


def banner(text: str) -> None:
    line = "=" * 70
    print(f"\n{line}\n  {text}\n{line}", flush=True)


# --- clavier / fenêtres -----------------------------------------------------------------------------

VK_CONTROL, VK_SHIFT, VK_MENU, VK_PRIOR, VK_NEXT = 0x11, 0x10, 0x12, 0x21, 0x22
_EXTENDED = {VK_PRIOR, VK_NEXT}


def keys(*combo: int) -> None:
    """Appuie la combinaison (ex. Ctrl+W) dans la fenêtre au premier plan."""
    user32 = ctypes.windll.user32
    for vk in combo:
        user32.keybd_event(vk, 0, 1 if vk in _EXTENDED else 0, 0)
        time.sleep(0.03)
    for vk in reversed(combo):
        user32.keybd_event(vk, 0, (1 if vk in _EXTENDED else 0) | 2, 0)
        time.sleep(0.03)
    time.sleep(0.4)


def chrome_in_front() -> bool:
    focus_chrome()
    return winlayout.window_process_name(winlayout.foreground_window()) == "chrome.exe"


def terminal_to_front() -> None:
    """Remet le terminal de la démo au premier plan pour le verdict (Windows Terminal ou console classique)."""
    user32 = ctypes.windll.user32
    target = []

    def visit(hwnd, _):
        if user32.IsWindowVisible(hwnd) and winlayout.window_process_name(hwnd) in ("WindowsTerminal.exe", "conhost.exe", "powershell.exe", "pwsh.exe"):
            target.append(hwnd)
        return True
    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(visit), 0)
    hwnd = target[0] if target else ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd:
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        user32.keybd_event(VK_MENU, 0, 2, 0)
        time.sleep(1)


# --- verdict d'un essai -----------------------------------------------------------------------------

def judge(note: str, rep: dict | None) -> tuple[str, str]:
    """('ok' | 'hors_site' | 'echec', raison) pour un remplissage WTJ."""
    if not rep:
        return "echec", f"pas de rapport de l'extension ({note})"
    state = rep.get("state") or {}
    if "welcometothejungle.com" not in (state.get("site") or rep.get("url") or ""):
        return "hors_site", f"la page a quitté WTJ ({state.get('site') or rep.get('url')})"
    if state.get("skipped"):
        return "echec", f"état non relevé : {state['skipped']}"
    crit = [c for c in state.get("criteria") or [] if not c.get("skip")]
    bad = [c["k"] for c in crit if not c["ok"]]
    code = (rep.get("stop") or {}).get("code")
    if not crit:
        return "echec", "aucun critère relevé"
    if bad:
        return "echec", "critères ratés : " + ", ".join(bad)
    if code not in OK_STOPS:
        return "echec", f"arrêt [{code}] {(rep.get('stop') or {}).get('text', '')}"
    return "ok", "formulaire rempli, bouton d'envoi prêt (non cliqué)"


# --- étapes -----------------------------------------------------------------------------------------

def precheck(port: int, want_video: bool) -> tuple[str | None, list[str]]:
    problems = []
    try:
        call(port, "/result", "chrome")
    except OSError:
        problems.append("programme local de remplissage arrêté : .\\fill.ps1 install (ou python fill.py)")
    try:
        gmail.get_service(interactive=False)
    except Exception as exc:  # noqa: BLE001
        problems.append(f"Gmail : {exc}")
    ffmpeg = find_ffmpeg() if want_video else None
    if want_video and not ffmpeg:
        problems.append("ffmpeg introuvable (winget install Gyan.FFmpeg)")
    if not _find_chrome():
        problems.append("Chrome introuvable")
    return ffmpeg, problems


def step_alertes(run_dir: Path) -> dict:
    banner("1/4  Alertes email (Gmail, lecture seule) -> offres Apec et HelloWork")
    lot = alertes.collect(days=3, sites=list(alertes.SITES), interactive=False)
    path = run_dir / "alertes_lot.json"
    path.write_text(json.dumps(lot, ensure_ascii=False, indent=1), encoding="utf-8")
    for o in lot[:8]:
        print(f"    [{o['source']}] {o['title'][:70]}")
    by_site = {s: sum(o["source"] == s for o in lot) for s in alertes.SITES}
    print(f"  {len(lot)} offre(s) -> {path}  (candidature sur ces sites : versions suivantes de la démo)")
    time.sleep(4)
    return {"total": len(lot), "par_site": by_site}


def step_wtj(args, port: int, chrome: str, profile: str, cfg: dict, report: dict) -> list[dict]:
    banner(f"2-3/4  WTJ « {args.query} » : préparation (CV + LM) puis remplissage de {args.n} offres")
    staging = REPO_ROOT / cfg["staging_dir"]
    staging.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    for previous in [REPO_ROOT / "output" / "copilot" / "wtj_lot_1.json"]:  # entreprises déjà candidatées pour de vrai
        if previous.exists():
            seen |= {wtj_prepare.org_of(o) for o in json.loads(previous.read_text(encoding="utf-8"))}
    offers_log: list[dict] = report["offres"]
    successes, total = 0, 0
    t_prev = time.time()
    for offer, entry in wtj_prepare.iter_offers([args.query], seen):
        prep = round(time.time() - t_prev)
        item = {**entry, "preparation_s": prep, "essais": []}
        offers_log.append(item)
        print(f"\n  offre {len(offers_log)} : {offer.company} -- {offer.title}  (recherche + CV + LM : {prep} s)")
        for attempt in range(1, MAX_TRIES_PER_OFFER + 1):
            if total >= MAX_TRIES_TOTAL:
                break
            if site_attempts(offer.source) >= MAX_SITE_ATTEMPTS:
                item["essais"].append({"verdict": "echec", "raison": f"règle des {MAX_SITE_ATTEMPTS} essais/jour atteinte"})
                report["arret"] = f"règle des {MAX_SITE_ATTEMPTS} essais par jour sur WTJ atteinte"
                return offers_log
            total += 1
            stage_files(offer, staging, cfg["file_name"])
            site_attempts(offer.source, 1)
            t0 = time.time()
            note = run_one(port, "chrome", chrome, profile, apply_url(offer), args.wait)
            rep = fetch_report(port, t0)
            verdict, reason = judge(note, rep)
            took = round(time.time() - t0)
            item["essais"].append({"n": attempt, "verdict": verdict, "raison": reason, "duree_s": took, "note": note,
                                   "criteres": [{"k": c["k"], "ok": c["ok"]} for c in ((rep or {}).get("state") or {}).get("criteria", [])],
                                   "capture": (rep or {}).get("shot")})
            print(f"    essai {attempt} ({total}/{MAX_TRIES_TOTAL}) : {verdict} -- {reason}  [{took} s]")
            if verdict == "ok":
                successes += 1
                break
            if chrome_in_front():  # onglet raté refermé : le diaporama ne montre que les réussites
                keys(VK_CONTROL, 0x57)
            if verdict == "hors_site":
                break  # réessayer ne la ramènera pas sur WTJ
        item["resultat"] = "ok" if item["essais"] and item["essais"][-1]["verdict"] == "ok" else "abandonnee"
        if successes >= args.n:
            break
        if total >= MAX_TRIES_TOTAL:
            report["arret"] = f"{MAX_TRIES_TOTAL} essais au total atteints"
            break
        t_prev = time.time()
    else:
        report["arret"] = "plus d'offre WTJ correspondante"
    return offers_log


def step_slideshow(n_ok: int) -> None:
    banner(f"4/4  Diaporama : les {n_ok} onglets remplis, prêts à l'envoi (jamais cliqué)")
    if not n_ok or not chrome_in_front():
        return
    keys(VK_CONTROL, 0x39)  # Ctrl+9 : dernier onglet
    for _ in range(n_ok - 1):
        keys(VK_CONTROL, VK_PRIOR)  # recule jusqu'au premier onglet réussi
    for i in range(n_ok):
        time.sleep(SLIDE_SECONDS)
        if i < n_ok - 1:
            keys(VK_CONTROL, VK_NEXT)


def write_report(run_dir: Path, report: dict) -> Path:
    (run_dir / "rapport.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# Démo SOS-JOB du {report['debut']}", "",
             f"**Verdict : {'VERT' if report['objectif_atteint'] else 'ROUGE'}** -- {report['reussies']}/{report['visees']} offres WTJ remplies "
             f"en {report['essais_total']} essai(s), durée {report['duree_s']} s.", ""]
    if report.get("arret"):
        lines += [f"Arrêt : {report['arret']}", ""]
    if report.get("alertes"):
        lines += [f"Alertes email : {report['alertes']['total']} offre(s) {report['alertes']['par_site']}", ""]
    lines += ["| Entreprise | Poste | Préparation | Essais | Résultat |", "|---|---|---|---|---|"]
    for o in report["offres"]:
        tries = " / ".join(f"{e.get('verdict')} ({e.get('raison')})" for e in o["essais"])
        lines.append(f"| {o['company']} | {o['title']} | {o['preparation_s']} s | {tries} | {o.get('resultat', '-')} |")
    if report.get("video"):
        lines += ["", f"Vidéo : {report['video']}"]
    path = run_dir / "rapport.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=3, help="offres WTJ à remplir")
    parser.add_argument("--query", default="Software Engineer")
    parser.add_argument("--no-video", action="store_true", help="mode TNR seul, sans enregistrement")
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--wait", type=float, default=7.0, help="secondes d'attente du chargement de la page")
    args = parser.parse_args()

    cfg = config.load_copilot()
    port = int(cfg.get("fill_server_port", 47321))
    profile = (yaml.safe_load(LOGIN_SITES.read_text(encoding="utf-8")) or {}).get("profile_directory", "") if LOGIN_SITES.exists() else ""
    chrome = _find_chrome()

    banner("0/4  Vérifications")
    ffmpeg, problems = precheck(port, not args.no_video)
    if problems:
        for p in problems:
            print(f"  ✗ {p}")
        raise SystemExit(1)
    print("  ✓ remplissage local, Gmail, " + ("ffmpeg, " if ffmpeg else "") + "Chrome")

    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    run_dir = REPO_ROOT / "output" / "demo" / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    report = {"debut": stamp, "requete": args.query, "visees": args.n, "offres": [], "etapes_s": {}}
    recorder = Recorder(ffmpeg, run_dir / "demo.mp4", args.fps) if ffmpeg else None
    start = time.time()
    try:
        if recorder:
            recorder.start()
            print(f"  ● enregistrement de l'écran -> {run_dir}")
        t = time.time()
        try:
            report["alertes"] = step_alertes(run_dir)
        except Exception as exc:  # noqa: BLE001 -- une source en panne n'empêche pas la suite (verdict rouge quand même)
            report["alertes"] = None
            report["erreur_alertes"] = str(exc)
            print(f"  ✗ alertes : {exc}")
        report["etapes_s"]["alertes"] = round(time.time() - t)
        t = time.time()
        step_wtj(args, port, chrome, profile, cfg, report)
        report["etapes_s"]["wtj"] = round(time.time() - t)
        n_ok = sum(o.get("resultat") == "ok" for o in report["offres"])
        t = time.time()
        step_slideshow(n_ok)
        report["etapes_s"]["diaporama"] = round(time.time() - t)
        terminal_to_front()
        report.update(reussies=n_ok, essais_total=sum(len(o["essais"]) for o in report["offres"]))
        report["objectif_atteint"] = n_ok >= args.n and report.get("alertes") is not None
        report["duree_s"] = round(time.time() - start)
        banner(f"Verdict : {'VERT' if report['objectif_atteint'] else 'ROUGE'} -- {n_ok}/{args.n} offres WTJ remplies "
               f"en {report['essais_total']} essai(s), {report['duree_s']} s")
        for o in report["offres"]:
            print(f"  {'✓' if o.get('resultat') == 'ok' else '✗'} {o['company']} -- {o['title'][:50]}  "
                  f"(prépa {o['preparation_s']} s, {len(o['essais'])} essai(s))")
        time.sleep(5)  # le verdict reste à l'écran dans la vidéo
    finally:
        if recorder:
            video = recorder.stop()
            report["video"] = str(video) if video else None
        report.setdefault("objectif_atteint", False)
        report.setdefault("reussies", sum(o.get("resultat") == "ok" for o in report["offres"]))
        report.setdefault("essais_total", sum(len(o["essais"]) for o in report["offres"]))
        report.setdefault("duree_s", round(time.time() - start))
        path = write_report(run_dir, report)
        print(f"\nRapport : {path}" + (f"\nVidéo : {report.get('video')}" if report.get("video") else ""))
    sys.exit(0 if report["objectif_atteint"] else 1)


if __name__ == "__main__":
    main()
