"""Navigateur headless partagé (Playwright), pour les sites dont les
données ne sont rendues qu'après exécution du JS côté client -- pas d'API
HTTP simple à reproduire (ex: état Nuxt serialisé, fragment htmx, clé
tierce injectée dynamiquement). Même politique de politesse que http.py :
User-Agent honnête, délai minimum entre deux navigations.

Un navigateur réel qui charge les pages comme le ferait un visiteur est
une lecture normale du site, pas un contournement -- à la différence
d'appeler directement un endpoint interne découvert dans le JS avec une
clé extraite à la main.
"""
from __future__ import annotations

import time
from contextlib import contextmanager

from playwright.sync_api import sync_playwright

from .http import USER_AGENT

MIN_DELAY_SECONDS = 1.5

_last_nav_at = 0.0


def _throttle() -> None:
    global _last_nav_at
    elapsed = time.monotonic() - _last_nav_at
    if elapsed < MIN_DELAY_SECONDS:
        time.sleep(MIN_DELAY_SECONDS - elapsed)
    _last_nav_at = time.monotonic()


@contextmanager
def page():
    """Un seul navigateur/onglet pour toute la durée du `with` (réutilisé
    entre plusieurs mots-clés d'un même fetch())."""
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        try:
            pg = b.new_page(user_agent=USER_AGENT)
            yield pg
        finally:
            b.close()


def goto(pg, url: str, *, wait_until: str = "load", timeout: int = 20000) -> None:
    _throttle()
    pg.goto(url, wait_until=wait_until, timeout=timeout)
