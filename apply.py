"""Copilot de candidature : parcourt les offres générées (CV + LM prêts, pas
encore traitées). Pour chacune : Chrome à gauche sur l'offre, CV/LM de l'offre
copiés dans le dossier d'upload (Explorateur en haut à droite, fenêtre fixe),
et un tableau de bord HTML d'avancement en bas à droite. Tu uploades
toi-même ; rien n'est soumis automatiquement.

Raccourcis globaux (marchent quelle que soit la fenêtre active) :
  Ctrl+Alt+Droite = candidaté   Ctrl+Alt+Gauche = offre précédente
  Ctrl+Alt+S = passer           Ctrl+Alt+Q = quitter
Usage : python apply.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import applications, config, dashboard, winlayout  # noqa: E402
from src.hotkeys import HotkeyListener  # noqa: E402
from src.offer import Offer  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent

_CHROME_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
)


def _find_chrome() -> str:
    chrome = shutil.which("chrome") or next((p for p in _CHROME_PATHS if Path(p).exists()), None)
    if not chrome:
        raise SystemExit("Chrome introuvable (chemins standards testés).")
    return chrome


def apply_url(offer: Offer) -> str:
    """Page du formulaire quand l'ATS la distingue de la description."""
    url = offer.url
    if offer.source == "lever" and not url.rstrip("/").endswith("/apply"):
        url = url.rstrip("/") + "/apply"
    elif offer.source == "ashby" and not url.rstrip("/").endswith("/application"):
        url = url.rstrip("/") + "/application"
    return url


def stage_files(offer: Offer, staging: Path, file_name: str) -> list[str]:
    """Copie CV/LM de l'offre sous des noms fixes. Retourne les avertissements."""
    cv, lm = applications.locate_pdfs(offer)
    warnings = []
    for label, src in (("CV", cv), ("LM", lm)):
        dest = staging / f"{label}_{file_name}.pdf"
        if src is None:
            dest.unlink(missing_ok=True)  # jamais laisser le fichier d'une autre offre
            warnings.append(f"{label} introuvable pour cette offre")
            continue
        try:
            shutil.copyfile(src, dest)
        except OSError as exc:
            warnings.append(f"{label} non copié ({exc}) -- ferme l'aperçu du PDF dans l'Explorateur")
    return warnings


class Layout:
    """Moitié gauche : navigateur. Moitié droite : Explorateur (haut), tableau de bord (bas)."""

    def __init__(self, cfg: dict, copilot_dir: Path) -> None:
        x, y, w, h = winlayout.work_area()
        left_w = int(w * float(cfg.get("browser_width_ratio", 0.5)))
        top_h = int(h * float(cfg.get("explorer_height_ratio", 0.5)))
        self.browser = (x, y, left_w, h)
        self.explorer = (x + left_w, y, w - left_w, top_h)
        self.dashboard = (x + left_w, y + top_h, w - left_w, h - top_h)
        self.chrome = _find_chrome()
        self.copilot_dir = copilot_dir
        self._browser_opened = False

    def open_explorer(self, folder: Path) -> None:
        subprocess.Popen(["explorer.exe", str(folder)])
        hwnd = winlayout.find_window("CabinetWClass", folder.name)
        if hwnd:
            winlayout.move_window(hwnd, *self.explorer)

    def open_dashboard(self, page: Path) -> None:
        # Profil Chrome séparé : sinon les offres s'ouvriraient dans la fenêtre du tableau de bord.
        x, y, w, h = self.dashboard
        subprocess.Popen([self.chrome, f"--app={page.resolve().as_uri()}",
                          f"--user-data-dir={self.copilot_dir / 'dashboard_profile'}",
                          "--no-first-run", "--no-default-browser-check",
                          f"--window-position={x},{y}", f"--window-size={w},{h}"])
        hwnd = winlayout.find_window("Chrome_WidgetWin_1", "SOS-JOB Copilot")
        if hwnd:
            winlayout.move_window(hwnd, *self.dashboard)

    def open_offer(self, url: str) -> None:
        if not url.startswith(("http://", "https://")):
            return
        if not self._browser_opened:
            x, y, w, h = self.browser
            subprocess.Popen([self.chrome, "--new-window", f"--window-position={x},{y}",
                              f"--window-size={w},{h}", url])
            time.sleep(2.0)
            hwnd = winlayout.foreground_window()
            if winlayout.window_class(hwnd) == "Chrome_WidgetWin_1":
                winlayout.move_window(hwnd, *self.browser)
            self._browser_opened = True
        else:
            subprocess.Popen([self.chrome, url])  # nouvel onglet dans la fenêtre Chrome existante


def compute_stats(session: list[tuple[str, Offer]], i: int, warnings: list[str]) -> dict:
    statuses = applications.statuses()
    done_keys = [k for k, _ in session if statuses.get(k) != applications.PENDING]
    applied = sum(1 for k, _ in session if statuses.get(k) == applications.APPLIED)
    key, offer = session[min(i, len(session) - 1)]
    total_by_source = Counter(o.source for _, o in session)
    done_by_source = Counter(o.source for k, o in session if k in done_keys)
    return {
        "total": len(session),
        "done": len(done_keys),
        "applied": applied,
        "skipped": len(done_keys) - applied,
        "current": {"title": offer.title.strip(), "company": offer.company, "location": offer.location,
                    "source": offer.source, "status": statuses.get(key, "pending"), "index": min(i, len(session) - 1) + 1},
        "per_source": [(s, done_by_source[s], n) for s, n in sorted(total_by_source.items())],
        "warnings": warnings,
    }


def main() -> None:
    cfg = config.load_copilot()
    session = applications.pending()
    if not session:
        print("Aucune offre en attente. Lance d'abord .\\run.ps1 pour générer des CV/LM.")
        return

    staging = REPO_ROOT / cfg["staging_dir"]
    staging.mkdir(parents=True, exist_ok=True)
    file_name = cfg["file_name"]
    copilot_dir = staging.parent
    page = copilot_dir / "dashboard.html"

    hotkeys = HotkeyListener()
    hotkeys.start()
    warnings = [f"raccourci '{n}' déjà pris par une autre application" for n in hotkeys.failed]

    layout = Layout(cfg, copilot_dir)
    dashboard.write(page, dashboard.render(compute_stats(session, 0, warnings)))
    layout.open_dashboard(page)
    layout.open_explorer(staging)

    print("Copilot lancé (tableau de bord en bas à droite). Ctrl+Alt+Q pour quitter.")
    try:
        i = 0
        while 0 <= i < len(session):
            key, offer = session[i]
            offer_warnings = stage_files(offer, staging, file_name)
            layout.open_offer(apply_url(offer))
            dashboard.write(page, dashboard.render(compute_stats(session, i, warnings + offer_warnings)))
            action = hotkeys.wait()
            if action == "right":
                applications.set_status(key, applications.APPLIED)
                i += 1
            elif action == "skip":
                applications.set_status(key, applications.SKIPPED)
                i += 1
            elif action == "left":
                i = max(0, i - 1)
            elif action == "quit":
                dashboard.write(page, dashboard.render(compute_stats(session, i, warnings), state="quit"))
                print("Arrêt. Reprise au prochain .\\apply.ps1 (les offres traitées ne reviennent pas).")
                return
        dashboard.write(page, dashboard.render(compute_stats(session, len(session) - 1, warnings), state="done"))
        print("Toutes les offres du lot ont été traitées.")
    finally:
        hotkeys.stop()


if __name__ == "__main__":
    main()
