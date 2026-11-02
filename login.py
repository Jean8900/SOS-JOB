"""Tournée de connexion : ouvre un à un, dans ton Chrome, les sites de input/login_sites.yaml.

Tu te connectes toi-même sur chaque site (ton gestionnaire de mots de passe remplit et enregistre) ;
la session est ensuite gardée par Chrome pendant des semaines, ce qui évite de se reconnecter à chaque
candidature. Ce programme ne lit pas les pages, ne prend aucune capture, ne voit ni ne stocke aucun
identifiant : il ouvre l'adresse et attend ton raccourci.

Raccourcis globaux : Ctrl+Alt+Droite = connecté (site suivant), Ctrl+Alt+S = passer,
Ctrl+Alt+Gauche = site précédent, Ctrl+Alt+Q = quitter.
Reprise : les sites déjà marqués « connecté » (output/logins.json) ne sont pas redemandés.

Usage : python login.py [--all] [--list] [--sites fichier.yaml] [--state fichier.json] [--chrome chemin]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apply import _find_chrome  # noqa: E402
from src.hotkeys import HotkeyListener  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_SITES = REPO_ROOT / "input" / "login_sites.yaml"
DEFAULT_STATE = REPO_ROOT / "output" / "logins.json"
DONE, SKIPPED = "done", "skipped"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "site"


def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        print(f"ATTENTION : {path.name} illisible, repart de zéro (l'ancien fichier n'est pas écrasé avant la 1re sauvegarde).")
        return {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)  # écriture atomique


def open_url(chrome: str, cfg: dict, url: str) -> None:
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"adresse refusée : {url}")
    args = [chrome]
    if cfg.get("profile_directory"):
        args.append(f"--profile-directory={cfg['profile_directory']}")
    args += list(cfg.get("chrome_args") or [])
    subprocess.Popen(args + [url])  # nouvel onglet dans la fenêtre Chrome existante


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="repasser aussi par les sites déjà connectés")
    ap.add_argument("--list", action="store_true", help="afficher l'état de chaque site et quitter")
    ap.add_argument("--sites", type=Path, default=DEFAULT_SITES)
    ap.add_argument("--state", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--chrome", help="chemin de chrome.exe (par défaut : Chrome installé)")
    args = ap.parse_args()

    cfg = yaml.safe_load(args.sites.read_text(encoding="utf-8")) or {}
    sites = [dict(s, slug=s.get("slug") or slug(s["name"])) for s in cfg.get("sites", []) if s.get("enabled", True)]
    state = load_state(args.state)

    if args.list:
        for s in sites:
            entry = state.get(s["slug"], {})
            print(f"{entry.get('status', 'à faire'):10} {s['name']}")
        return

    todo = sites if args.all else [s for s in sites if state.get(s["slug"], {}).get("status") != DONE]
    if not todo:
        print("Tous les sites de la liste sont déjà marqués connectés (`--all` pour repasser dessus).")
        return

    chrome = args.chrome or _find_chrome()
    hotkeys = HotkeyListener()
    hotkeys.start()
    if hotkeys.failed:
        print("ATTENTION : raccourcis déjà pris par une autre application :", ", ".join(hotkeys.failed),
              "(copilot apply.ps1 en cours ?)")
    print(f"{len(todo)} site(s) à parcourir. Ctrl+Alt+→ = connecté, Ctrl+Alt+S = passer, "
          "Ctrl+Alt+← = précédent, Ctrl+Alt+Q = quitter.")
    print("Tu te connectes toi-même ; ce programme ne voit aucun identifiant et ne lit pas les pages.\n")

    done_now = 0
    try:
        i = 0
        while 0 <= i < len(todo):
            site = todo[i]
            print(f"[{i + 1}/{len(todo)}] {site['name']} -> {site['url']}")
            try:
                open_url(chrome, cfg, site["url"])
            except ValueError as exc:
                print("  ", exc)
                i += 1
                continue
            action = hotkeys.wait()
            if action == "right":
                state[site["slug"]] = {"status": DONE, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                save_state(args.state, state)
                done_now += 1
                i += 1
            elif action == "skip":
                if state.get(site["slug"], {}).get("status") != DONE:
                    state[site["slug"]] = {"status": SKIPPED, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                    save_state(args.state, state)
                i += 1
            elif action == "left":
                i = max(0, i - 1)
            elif action == "quit":
                print("Arrêt. Reprise au prochain .\\login.ps1 (les sites connectés ne reviennent pas).")
                return
        total_done = sum(1 for s in sites if state.get(s["slug"], {}).get("status") == DONE)
        print(f"\nTerminé : {done_now} connecté(s) dans cette passe, {total_done}/{len(sites)} au total.")
    finally:
        hotkeys.stop()


if __name__ == "__main__":
    main()
