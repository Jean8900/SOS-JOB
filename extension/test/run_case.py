"""Banc d'essai de l'extension : ouvre une page dans un Chromium (ou Edge) qui charge l'extension,
envoie un vrai Ctrl+Alt+Espace, et affiche ce qui a été rempli. Ne clique jamais rien d'autre.

Usage : python extension\\test\\run_case.py <url> [--browser chrome|edge] [--name cas]
Prérequis : programme local lancé (`.\\fill.ps1 status`).
Sortie : message de l'extension, champs remplis, capture dans output\\copilot\\ext_tests\\.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src import winlayout  # noqa: E402

EXTENSION = REPO_ROOT / "extension"
OUT_DIR = REPO_ROOT / "output" / "copilot" / "ext_tests"
PROFILES = REPO_ROOT / "output" / "copilot"
VK_CTRL, VK_ALT, VK_SPACE = 0x11, 0x12, 0x20
# Boutons d'envoi : jamais cliqués, même demandés par --click.
FORBIDDEN_CLICK = re.compile(r"submit|envoyer|soumettre|candidater|postuler|valider|confirmer|send|finish|terminer", re.I)


def connected_instances(browser: str, port: int = 47321) -> dict:
    """Instances d'extension vues récemment par le programme local ({id: âge en s})."""
    req = urllib.request.Request(f"http://127.0.0.1:{port}/status?b={browser}", headers={"X-SOSJOB": "1"})
    return json.load(urllib.request.urlopen(req, timeout=3))["instances"]

FILLED_JS = """() => [...document.querySelectorAll('input, textarea, select, button[aria-haspopup]')]
  .filter(e => e.style.outline.includes('245, 166, 35') || e.closest('[style*="245, 166, 35"]'))
  .map(e => (e.getAttribute('aria-label') || e.name || e.id || e.tagName) + ' = ' + String(e.value || e.innerText || e.checked).slice(0, 80).replace(/\\n/g, ' '))"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--browser", choices=["chrome", "edge"], default="chrome")
    ap.add_argument("--name", default="cas")
    ap.add_argument("--timeout", type=int, default=150)
    ap.add_argument("--click", action="append", default=[], help="texte d'un bouton à cliquer avant de remplir (ouvrir le formulaire) ; jamais un bouton d'envoi")
    args = ap.parse_args()
    for text in args.click:
        if FORBIDDEN_CLICK.search(text):
            raise SystemExit(f"refusé : « {text} » ressemble à un bouton d'envoi")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    user32 = ctypes.windll.user32
    profile = PROFILES / f"test_profile_{args.browser}"
    shutil.rmtree(profile, ignore_errors=True)  # profil neuf : nouvelle instance d'extension, aucun ordre d'écho
    before = set(connected_instances(args.browser))
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(profile), headless=False,
            channel="msedge" if args.browser == "edge" else None,
            args=[f"--disable-extensions-except={EXTENSION}", f"--load-extension={EXTENSION}", "--window-size=1100,900"],
            viewport={"width": 1000, "height": 800})
        try:
            if not ctx.service_workers:
                ctx.wait_for_event("serviceworker", timeout=15000)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            deadline = time.time() + 40
            while time.time() < deadline and not set(connected_instances(args.browser)) - before:
                time.sleep(0.5)  # attendre que l'extension de CE navigateur écoute le programme local
            page.goto(args.url, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            for text in args.click:  # ouvrir le formulaire (jamais un envoi)
                page.get_by_text(text, exact=False).first.click(timeout=8000)
                page.wait_for_timeout(3500)

            hwnd = winlayout.find_window("Chrome_WidgetWin_1", page.title()[:12], timeout=5)
            user32.keybd_event(0x12, 0, 0, 0)   # touche Alt : autorise SetForegroundWindow
            user32.keybd_event(0x12, 0, 2, 0)
            user32.SetForegroundWindow(hwnd)
            page.wait_for_timeout(800)
            print("fenêtre active :", winlayout.window_process_name(winlayout.foreground_window()))

            for vk in (VK_CTRL, VK_ALT, VK_SPACE):
                user32.keybd_event(vk, 0, 0, 0)
            for vk in (VK_SPACE, VK_ALT, VK_CTRL):
                user32.keybd_event(vk, 0, 2, 0)

            started = time.time()
            toast = ""
            while time.time() - started < args.timeout:
                page.wait_for_timeout(1500)
                toast = page.evaluate("document.getElementById('sosjob-toast')?.textContent || ''")
                if "pré-rempli" in toast or "aucun champ" in toast or "échec" in toast or "désactivé" in toast:
                    break
            print(f"message ({time.time() - started:.0f}s) :", toast or "(aucun : raccourci non reçu ou extension non connectée)")
            for line in page.evaluate(FILLED_JS):
                print("  rempli :", line)
            shot = OUT_DIR / f"{args.name}.png"
            page.screenshot(path=str(shot), full_page=True)
            print("capture :", shot)
        finally:
            ctx.close()


if __name__ == "__main__":
    main()
