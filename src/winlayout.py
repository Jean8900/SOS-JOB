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


# --- Navigation dans l'onglet actif d'une fenêtre (sans ouvrir de nouvel onglet) ---

_VK_CONTROL, _VK_MENU, _VK_SHIFT, _VK_L, _VK_DELETE, _VK_RETURN = 0x11, 0x12, 0x10, 0x4C, 0x2E, 0x0D
_KEYEVENTF_KEYUP, _KEYEVENTF_UNICODE = 0x0002, 0x0004
_INPUT_KEYBOARD = 1


class _KeyboardInput(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _MouseInput(ctypes.Structure):  # sert uniquement à donner à INPUT sa taille réelle (union)
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _InputUnion(ctypes.Union):
    _fields_ = [("ki", _KeyboardInput), ("mi", _MouseInput)]


class _Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _InputUnion)]


def _send_key(vk: int = 0, char: str = "", up: bool = False) -> None:
    flags = _KEYEVENTF_KEYUP if up else 0
    if char:
        flags |= _KEYEVENTF_UNICODE
    inp = _Input(_INPUT_KEYBOARD, _InputUnion(ki=_KeyboardInput(vk, ord(char) if char else 0, flags, 0, 0)))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


def is_window(hwnd: int) -> bool:
    return bool(user32.IsWindow(hwnd))


def _wait_modifiers_released(timeout: float = 3.0) -> None:
    """Le raccourci global est encore enfoncé quand on est appelé : les touches simulées se combineraient avec Ctrl+Alt."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in (_VK_CONTROL, _VK_MENU, _VK_SHIFT)):
        time.sleep(0.05)


def navigate_active_tab(hwnd: int, url: str) -> None:
    """Met la fenêtre au premier plan et charge `url` dans son onglet actif (Ctrl+L, saisie, Entrée).
    N'utilise pas le presse-papier : il sert à coller la LM texte."""
    _wait_modifiers_released()
    user32.ShowWindow(hwnd, _SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.25)
    _send_key(_VK_CONTROL); _send_key(_VK_L); _send_key(_VK_L, up=True); _send_key(_VK_CONTROL, up=True)
    time.sleep(0.15)
    for ch in url:
        _send_key(char=ch); _send_key(char=ch, up=True)
    _send_key(_VK_DELETE); _send_key(_VK_DELETE, up=True)  # retire l'auto-complétion en ligne de la barre d'adresse
    _send_key(_VK_RETURN); _send_key(_VK_RETURN, up=True)


def window_process_name(hwnd: int) -> str:
    """Nom du .exe qui possède la fenêtre (ex. « chrome.exe », « msedge.exe »), en minuscules."""
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if ctypes.windll.kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value.rsplit("\\", 1)[-1].lower()
        return ""
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)
