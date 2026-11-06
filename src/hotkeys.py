"""Raccourcis clavier globaux (Ctrl+Alt+...) via RegisterHotKey : fonctionnent
quelle que soit la fenêtre qui a le focus. Seules les combinaisons
enregistrées sont reçues (pas de capture générale du clavier, pas de droits
admin) ; elles sont libérées à l'arrêt."""
from __future__ import annotations

import ctypes
import queue
import threading
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

_MOD_ALT, _MOD_CONTROL, _MOD_NOREPEAT = 0x0001, 0x0002, 0x4000
_WM_HOTKEY, _WM_QUIT = 0x0312, 0x0012

KEYS = {"right": 0x27, "left": 0x25, "skip": 0x53, "quit": 0x51}  # flèche droite/gauche, S, Q


class HotkeyListener:
    def __init__(self, keys: dict[str, int] | None = None) -> None:
        self._keys = keys or KEYS
        self.actions: queue.Queue[str] = queue.Queue()
        self.failed: list[str] = []
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread_id = 0

    def start(self) -> None:
        self._thread.start()
        self._ready.wait(timeout=5)

    def _run(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()
        by_id = {}
        for i, (action, vk) in enumerate(self._keys.items(), start=1):
            if user32.RegisterHotKey(None, i, _MOD_CONTROL | _MOD_ALT | _MOD_NOREPEAT, vk):
                by_id[i] = action
            else:
                self.failed.append(action)  # combinaison déjà prise par une autre application
        self._ready.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == _WM_HOTKEY and msg.wParam in by_id:
                self.actions.put(by_id[msg.wParam])
        for i in by_id:
            user32.UnregisterHotKey(None, i)

    def stop(self) -> None:
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, _WM_QUIT, 0, 0)
            self._thread.join(timeout=2)

    def wait(self) -> str:
        """Bloque jusqu'à la prochaine action : right | left | skip | quit."""
        while True:
            try:
                return self.actions.get(timeout=0.5)
            except queue.Empty:
                continue
