"""Session HTTP partagée par les connecteurs : User-Agent honnête, retries
raisonnables, et un délai minimum entre deux requêtes (politesse, cf. brief
lot 1 : "au moins 1 à 2s entre deux requêtes, User-Agent honnête")."""
from __future__ import annotations

import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "SOS-JOB/0.1 (usage personnel, recherche d'emploi -- contact: jean.martini8900@gmail.com)"

MIN_DELAY_SECONDS = 1.5

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": USER_AGENT,
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
})
SESSION.mount("https://", HTTPAdapter(max_retries=Retry(
    total=2, status_forcelist=[429, 502, 503, 504], allowed_methods=["GET", "POST"],
)))

_last_request_at = 0.0


def _throttle() -> None:
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < MIN_DELAY_SECONDS:
        time.sleep(MIN_DELAY_SECONDS - elapsed)
    _last_request_at = time.monotonic()


def get(url: str, **kwargs) -> requests.Response:
    _throttle()
    return SESSION.get(url, timeout=kwargs.pop("timeout", (10, 30)), **kwargs)


def post(url: str, **kwargs) -> requests.Response:
    _throttle()
    return SESSION.post(url, timeout=kwargs.pop("timeout", (10, 30)), **kwargs)
