"""Positionnement de fenêtres Windows (ctypes, aucune dépendance)."""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

_SW_RESTORE = 9
_SWP_NOZORDER, _SWP_SHOWWINDOW = 0x0004, 0x0040
_SPI_GETWORKAREA = 48


def work_area() -> tuple[int, int, int, int]:
    """(x, y, largeur, hauteur) de l'écran hors barre des tâches."""
    rect = wintypes.RECT()
    user32.SystemParametersInfoW(_SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


_DWMWA_EXTENDED_FRAME_BOUNDS = 9


def _frame_insets(hwnd: int) -> tuple[int, int, int, int]:
    """Bordures invisibles (ombre) de Windows 10/11 autour de la zone visible : (gauche, haut, droite, bas)."""
    outer, visible = wintypes.RECT(), wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(outer))
    ctypes.windll.dwmapi.DwmGetWindowAttribute(
        hwnd, _DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(visible), ctypes.sizeof(visible))
    return (visible.left - outer.left, visible.top - outer.top,
            outer.right - visible.right, outer.bottom - visible.bottom)


def move_window(hwnd: int, x: int, y: int, w: int, h: int) -> None:
    """Place la partie VISIBLE de la fenêtre exactement sur (x, y, w, h), sans chevauchement."""
    user32.ShowWindow(hwnd, _SW_RESTORE)
    user32.SetWindowPos(hwnd, 0, x, y, w, h, _SWP_NOZORDER | _SWP_SHOWWINDOW)
    left, top, right, bottom = _frame_insets(hwnd)
    user32.SetWindowPos(hwnd, 0, x - left, y - top, w + left + right, h + top + bottom,
                        _SWP_NOZORDER | _SWP_SHOWWINDOW)


def foreground_window() -> int:
    return user32.GetForegroundWindow()


def window_class(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def window_title(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def find_window(class_name: str, title: str, timeout: float = 6.0) -> int | None:
    """Attend jusqu'à `timeout` s une fenêtre visible de cette classe dont le titre commence par `title`
    (l'Explorateur ajoute un suffixe localisé : "dossier : Explorateur de fichiers")."""
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _visit(hwnd, _):
        if user32.IsWindowVisible(hwnd) and window_class(hwnd) == class_name and window_title(hwnd).startswith(title):
            found.append(hwnd)
        return True

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found.clear()
        user32.EnumWindows(_visit, 0)
        if found:
            return found[0]
        time.sleep(0.3)
    return None
