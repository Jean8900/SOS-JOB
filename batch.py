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


def lot_offers(n: int, skip: int) -> list[tuple[str, object]]:
    """Offres préparées par wtj_prepare.py (output/copilot/wtj_lot.json), de la skip-ième à la skip+n-ième."""
    lot = json.loads((REPO_ROOT / "output" / "copilot" / "wtj_lot.json").read_text(encoding="utf-8"))
    offers = [Offer(source=o["source"], source_id=o["source_id"], url=o["url"], url_canonique=o["url"], title=o["title"],
                    company=o["company"], location=o.get("location", "")) for o in lot]
    return [(o.source_id, o) for o in offers[skip:skip + n]]


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


def save(report: list[dict]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", type=int, default=10)
    parser.add_argument("--source")
    parser.add_argument("--lot", action="store_true", help="offres de wtj_prepare.py au lieu des offres en attente")
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

    offers = lot_offers(args.n, args.skip) if args.lot else pick(args.n, args.source)
    if not offers:
        raise SystemExit("Aucune offre en attente avec CV et LM générés (.\\run.ps1).")
    print(f"{len(offers)} offre(s), une par onglet de ton Chrome. Ne touche pas au clavier pendant le lot.")

    report: list[dict] = []
    waiting: list[tuple[dict, object]] = []

    def process(offer, entry: dict) -> None:
        stage_files(offer, staging, cfg["file_name"])
        entry["note"] = run_one(port, "chrome", chrome, profile, apply_url(offer), args.wait)
        entry["login_needed"] = "connexion demandée" in entry["note"]
        print(f"  [{entry['source']}] {entry['title'][:50]} -> {entry['note']}")
        save(report)

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
