"""Lot de candidatures dans TON Chrome : une dizaine d'offres variées, un onglet chacune, remplissage au plus loin.

Pour chaque offre : copie le CV et la LM de l'offre dans le dossier d'upload, ouvre l'offre dans ton Chrome
(session et gestionnaire de mots de passe habituels), puis commande à l'extension le même remplissage que
Ctrl+Alt+Espace (champs, CV/LM, étapes suivantes). Jamais de clic sur un envoi : l'extension s'arrête avant.
Les onglets restent ouverts. Une offre qui demande une connexion est mise de côté ; à la fin tu te connectes
dans ces onglets puis Ctrl+Alt+Droite : elles sont reprises. Aucune page n'est lue, aucune capture n'est prise.
Le programme local (.\\fill.ps1 install) doit tourner.

Usage : python batch.py [-n 10] [--source lever] [--wait 7]
"""
from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply import _find_chrome, apply_url, stage_files  # noqa: E402
from src import applications, config  # noqa: E402
from src.hotkeys import HotkeyListener  # noqa: E402
from src.offer import Offer  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent
REPORT = REPO_ROOT / "output" / "copilot" / "batch_report.json"
LOGIN_SITES = REPO_ROOT / "input" / "login_sites.yaml"
OFFER_TIMEOUT = 360  # secondes par offre (rédaction des réponses par Claude à chaque étape)


def pick(n: int, source: str | None) -> list[tuple[str, object]]:
    """n offres en alternant les sources (variété), CV et LM présents."""
    by_source = defaultdict(list)
    for key, offer in applications.pending():
        cv, lm = applications.locate_pdfs(offer)
        if cv and lm and (not source or offer.source == source):
            by_source[offer.source].append((key, offer))
    mixed = [x for group in itertools.zip_longest(*by_source.values()) for x in group if x]
    return mixed[:n]


def lot_offers(n: int, skip: int, lot_file: str | None = None) -> list[tuple[str, object]]:
    """Offres d'un lot préparé (wtj_prepare.py -> wtj_lot.json, ou --lot-file), de la skip-ième à la skip+n-ième."""
    path = Path(lot_file) if lot_file else REPO_ROOT / "output" / "copilot" / "wtj_lot.json"
    lot = json.loads(path.read_text(encoding="utf-8"))
    offers = [Offer(source=o["source"], source_id=o["source_id"], url=o["url"], url_canonique=o["url"], title=o["title"],
                    company=o["company"], location=o.get("location", ""), description=o.get("description", "")) for o in lot]
    return [(o.source_id, o) for o in offers[skip:skip + n]]


def ensure_pdfs(offer) -> None:
    """Génère CV et LM de l'offre s'ils n'existent pas encore."""
    from src import cv_builder, lm_builder
    cv, lm = applications.locate_pdfs(offer)
    if cv is None:
        cv_builder.generate_cv_for_job(offer)
    if lm is None:
        lm_builder.generate_lm_for_job(offer)


def call(port: int, route: str, browser: str) -> dict:
    request = urllib.request.Request(f"http://127.0.0.1:{port}{route}?b={browser}", headers={"X-SOSJOB": "1"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read())


def open_in_chrome(chrome: str, url: str, profile: str) -> None:
    args = [chrome] + ([f"--profile-directory={profile}"] if profile else []) + [url]
    subprocess.Popen(args)


def focus_chrome() -> None:
    """Remet une fenêtre Chrome au premier plan (l'extension n'agit que si sa fenêtre a le focus)."""
    import ctypes
    from src import winlayout
    user32 = ctypes.windll.user32
    found = []

    def visit(hwnd, _):
        if user32.IsWindowVisible(hwnd) and winlayout.window_process_name(hwnd) == "chrome.exe"                 and winlayout.window_class(hwnd) == "Chrome_WidgetWin_1" and "chrome://" not in winlayout.window_title(hwnd)                 and not winlayout.window_title(hwnd).startswith("Extensions"):
            found.append(hwnd)
        return True
    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(visit), 0)
    if found and winlayout.window_process_name(winlayout.foreground_window()) != "chrome.exe":
        user32.keybd_event(0x12, 0, 0, 0)
        user32.SetForegroundWindow(found[0])
        user32.keybd_event(0x12, 0, 2, 0)
        time.sleep(1)


def run_one(port: int, browser: str, chrome: str, profile: str, url: str, wait: float) -> str:
    open_in_chrome(chrome, url, profile)
    time.sleep(wait)  # chargement de la page
    focus_chrome()
    if not call(port, "/trigger", browser).get("started"):
        return "ordre refusé : un remplissage est déjà en cours"
    deadline = time.time() + OFFER_TIMEOUT
    while time.time() < deadline:
        time.sleep(2)
        result = call(port, "/result", browser)
        if not result["busy"]:
            return result["note"] or "terminé (sans compte rendu)"
    return "délai dépassé"


def fetch_report(port: int, started: float) -> dict | None:
    """Rapport structuré de l'extension pour le remplissage qui vient de finir (None avec une ancienne extension)."""
    try:
        rep = call(port, "/report", "chrome").get("report")
    except OSError:
        return None
    return rep if rep and rep.get("ts", 0) >= started else None


def criteria_line(rep: dict | None) -> str:
    crit = ((rep or {}).get("state") or {}).get("criteria") or []
    return "  ".join(f"{'○' if c.get('skip') else ('✓' if c['ok'] else '✗')} {c['k']}" for c in crit)


def debug_block(rep: dict) -> str:
    """Trace, état final et capture d'une offre, en un bloc."""
    out = []
    for st in rep.get("steps", []):
        out.append(f"      étape {st.get('n')} : champs={st.get('filled', 0)} fichiers={st.get('uploaded', 0)} clic={st.get('clicked') or '-'} avancé={st.get('moved', '-')}")
    for err in rep.get("errors", []):
        out.append(f"      ERREUR étape {err.get('step')} [{err.get('kind')}] {err.get('where')} : {err.get('msg')}")
    for c in ((rep.get("state") or {}).get("criteria") or []):
        out.append(f"      {'○' if c.get('skip') else ('✓' if c['ok'] else '✗')} {c['k']} {c.get('v', '')}")
    stop = rep.get("stop") or {}
    out.append(f"      arrêt [{stop.get('code')}] {stop.get('text')}")
    snap = rep.get("snapshot")
    if snap and not snap.get("skipped"):
        btns = [f"{b['label']}({b['type'] or b['tag']}{',off' if b['disabled'] else ''}{'' if b['visible'] else ',caché'})" for b in snap.get("buttons", []) if b["label"]][:25]
        out.append("      boutons : " + " | ".join(btns))
    if rep.get("shot"):
        out.append(f"      capture : {rep['shot']}")
    return "\n".join(out)


MAX_REPLAYS = 5  # par offre et par jour : certains essais laissent des traces dans le compte du site (un CV de plus sur Free-Work)
REPLAYS = REPO_ROOT / "output" / "copilot" / "replays.json"


def count_replay(url: str) -> int:
    """Incrémente et renvoie le nombre de passages du jour sur cette offre."""
    today = time.strftime("%Y-%m-%d")
    try:
        data = json.loads(REPLAYS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if data.get("_day") != today:
        data = {"_day": today}
    data[url] = data.get(url, 0) + 1
    REPLAYS.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data[url]


def save(report: list[dict]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=10)
    parser.add_argument("--source")
    parser.add_argument("--lot", action="store_true", help="offres de wtj_prepare.py au lieu des offres en attente")
    parser.add_argument("--lot-file", help="fichier JSON d'offres (source, source_id, url, title, company, description)")
    parser.add_argument("--generate", action="store_true", help="générer CV et LM manquants avant d'ouvrir")
    parser.add_argument("--debug", action="store_true", help="affiche trace, état final, instantané et capture de chaque offre")
    parser.add_argument("--force-replay", action="store_true", help=f"passer outre le plafond de {MAX_REPLAYS} passages par offre et par jour")
    parser.add_argument("--no-files", action="store_true", help="ne dépose ni CV ni LM (déboguer les champs sans ajouter de documents au compte du site)")
    parser.add_argument("--skip", type=int, default=0, help="avec --lot : nombre d'offres à sauter")
    parser.add_argument("--wait", type=float, default=7.0, help="secondes d'attente du chargement de la page")
    args = parser.parse_args()

    cfg = config.load_copilot()
    port = int(cfg.get("fill_server_port", 47321))
    staging = REPO_ROOT / cfg["staging_dir"]
    staging.mkdir(parents=True, exist_ok=True)
    profile = (yaml.safe_load(LOGIN_SITES.read_text(encoding="utf-8")) or {}).get("profile_directory", "") if LOGIN_SITES.exists() else ""
    chrome = _find_chrome()
    try:
        call(port, "/result", "chrome")
    except OSError:
        raise SystemExit("Programme local arrêté : lance .\\fill.ps1 install (ou python fill.py).")

    offers = lot_offers(args.n, args.skip, args.lot_file) if (args.lot or args.lot_file) else pick(args.n, args.source)
    if not offers:
        raise SystemExit("Aucune offre en attente avec CV et LM générés (.\\run.ps1).")
    print(f"{len(offers)} offre(s), une par onglet de ton Chrome. Ne touche pas au clavier pendant le lot.")

    report: list[dict] = []
    waiting: list[tuple[dict, object]] = []

    def process(offer, entry: dict) -> None:
        if count_replay(entry["url"]) > MAX_REPLAYS and not args.force_replay:
            entry["note"] = f"plafond de {MAX_REPLAYS} passages par jour atteint (--force-replay pour passer outre)"
            entry["login_needed"] = False
            print(f"  [{entry['source']}] {entry['title'][:50]} -> {entry['note']}")
            return
        if args.no_files:
            for f in staging.glob("*"):
                f.unlink(missing_ok=True)
        else:
            stage_files(offer, staging, cfg["file_name"])
        started = time.time()
        entry["note"] = run_one(port, "chrome", chrome, profile, apply_url(offer), args.wait)
        entry["login_needed"] = "connexion demandée" in entry["note"]
        rep = fetch_report(port, started)
        entry["criteria"] = [{"k": c["k"], "ok": c["ok"]} for c in ((rep or {}).get("state") or {}).get("criteria", [])]
        print(f"  [{entry['source']}] {entry['title'][:50]} -> {entry['note']}")
        if rep and criteria_line(rep):
            print(f"      {criteria_line(rep)}")
        if rep and args.debug:
            print(debug_block(rep))
        save(report)

    if args.generate:  # CV et LM manquants, avant d'ouvrir quoi que ce soit
        for _, offer in offers:
            print(f"  CV/LM : {offer.company}")
            ensure_pdfs(offer)

    for key, offer in offers:
        entry = {"key": key, "source": offer.source, "title": offer.title, "company": offer.company, "url": apply_url(offer)}
        report.append(entry)
        process(offer, entry)
        if entry["login_needed"]:
            waiting.append((entry, offer))

    if waiting:
        print(f"\n{len(waiting)} offre(s) demandent une connexion : connecte-toi dans leurs onglets (gestionnaire de mots de passe),")
        print("puis Ctrl+Alt+Droite pour les reprendre (Ctrl+Alt+Q pour laisser tomber).")
        hotkeys = HotkeyListener()
        hotkeys.start()
        try:
            action = hotkeys.wait()
            if action == "right":
                for entry, offer in waiting:
                    process(offer, entry)
        finally:
            hotkeys.stop()

    print(f"\nTerminé. Compte rendu : {REPORT}")


if __name__ == "__main__":
    main()
