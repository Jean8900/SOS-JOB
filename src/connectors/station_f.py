"""Connecteur Station F (jobs.stationf.co) -- job 1 (analyse) :

Plateforme WelcomeKit/Algolia. La recherche `instantsearch.js` appelle
l'API Algolia directement depuis le navigateur, mais la clé de recherche
n'est injectée que par le JS exécuté côté client -- absente du HTML
initial. On utilise donc un navigateur headless (voir `browser.py`) qui
charge `/search?query=...` exactement comme un visiteur, puis on lit les
résultats rendus dans le DOM (`.ais-Hits-item a.jobs-item-link`).
"""
from __future__ import annotations

from ..offer import Offer
from . import browser

SOURCE = "station_f"
BASE_URL = "https://jobs.stationf.co"
SEARCH_URL = f"{BASE_URL}/search"

_CONTRACT_MAP = {
    "full-time": "full_time",
    "part-time": "part_time",
    "internship": "internship",
    "apprenticeship": "apprenticeship",
    "temporary": "temporary",
    "vie": "vie",
    "freelance": "freelance",
}


def _contract_type(raw: str) -> str:
    key = raw.strip().lower()
    return _CONTRACT_MAP.get(key, key.replace(" ", "_"))


def _to_offer(anchor) -> Offer | None:
    href = anchor.get_attribute("href")
    if not href:
        return None
    url = BASE_URL + href
    title_el = anchor.query_selector(".job-title")
    company_el = anchor.query_selector(".job-company")
    contract_el = anchor.query_selector(".job-contract-type")
    office_el = anchor.query_selector(".job-office")
    title = (title_el.inner_text() if title_el else "").strip()
    if not title:
        return None
    return Offer(
        source=SOURCE,
        source_id=href.strip("/"),
        url=url,
        url_canonique=url,
        title=title,
        company=(company_el.inner_text().strip() if company_el else ""),
        location=(office_el.inner_text().strip() if office_el else ""),
        contract_type=_contract_type(contract_el.inner_text() if contract_el else ""),
        description="",
    )


def fetch(max_results: int = 5) -> list[Offer]:
    from .. import config
    criteria = config.load_criteria()
    keywords = list(criteria.get("professions") or []) + list(criteria.get("stack") or [])

    offers: dict[str, Offer] = {}
    with browser.page() as pg:
        for keyword in keywords:
            if len(offers) >= max_results:
                break
            browser.goto(pg, f"{SEARCH_URL}?query={keyword.replace(' ', '+')}")
            try:
                pg.wait_for_selector(".ais-Hits-item", timeout=8000)
            except Exception:
                continue
            for anchor in pg.query_selector_all(".ais-Hits-item a.jobs-item-link"):
                offer = _to_offer(anchor)
                if offer is not None:
                    offers.setdefault(offer.source_id, offer)
                if len(offers) >= max_results:
                    break
    return list(offers.values())[:max_results]
