"""Connecteur Jobs that make sense (jobs.makesense.org) -- job 1 (analyse) :

Nuxt 3, données sérialisées côté serveur avec interning de variables --
illisible de façon fiable en parsant le HTML brut (cf. `README.md`). Les
~20 premières offres sont en revanche bien présentes dans le DOM une fois
le JS exécuté (`a.job__link`), donc un navigateur headless (voir
`browser.py`) suffit : pas besoin de scroller pour `max_results <= 20`.
Le paramètre `query` de l'URL de recherche n'a pas d'effet de filtre
mesurable (site généraliste "impact", pas de full-text fiable) -- comme
pour Choisir le service public, le tri se fait entièrement côté
`matcher.py`.
"""
from __future__ import annotations

import re

from ..offer import Offer
from . import browser

SOURCE = "jobs_that_make_sense"
BASE_URL = "https://jobs.makesense.org"
SEARCH_URL = f"{BASE_URL}/fr/s/jobs"

_CONTRACT_KEYWORDS = {
    "cdi": "full_time",
    "cdd": "temporary",
    "stage": "internship",
    "alternance": "apprenticeship",
    "freelance": "freelance",
    "bénévolat": "volunteering",
    "service civique": "civic_service",
    "intérim": "temporary",
}


def _contract_type(metas: list[str]) -> str:
    for meta in metas:
        key = meta.strip().lower()
        if key in _CONTRACT_KEYWORDS:
            return _CONTRACT_KEYWORDS[key]
    return ""


def _location(metas: list[str]) -> str:
    for meta in metas:
        if re.match(r"^[^,]+,\s*[^,]+$", meta.strip()):
            return meta.strip()
    return ""


def _to_offer(anchor) -> Offer | None:
    href = (anchor.get_attribute("href") or "").split("?")[0]
    if not href:
        return None
    title = (anchor.query_selector(".job__title").inner_text() or "").strip() if anchor.query_selector(".job__title") else ""
    if not title:
        return None
    company_el = anchor.query_selector(".job__company")
    mission_el = anchor.query_selector(".job__mission")
    metas = [m.inner_text().strip() for m in anchor.query_selector_all(".meta") if m.inner_text().strip()]
    url = BASE_URL + href
    return Offer(
        source=SOURCE,
        source_id=href.strip("/").split("/")[-1],
        url=url,
        url_canonique=url,
        title=title,
        company=(company_el.inner_text().strip() if company_el else ""),
        location=_location(metas),
        contract_type=_contract_type(metas),
        description=(mission_el.inner_text().strip() if mission_el else ""),
    )


def fetch(max_results: int = 5) -> list[Offer]:
    from .. import config
    criteria = config.load_criteria()
    keywords = list(criteria.get("professions") or []) + list(criteria.get("stack") or []) or [""]

    offers: dict[str, Offer] = {}
    with browser.page() as pg:
        for keyword in keywords:
            if len(offers) >= max_results:
                break
            url = SEARCH_URL + (f"?query={keyword.replace(' ', '+')}" if keyword else "")
            browser.goto(pg, url)
            try:
                pg.wait_for_selector("a.job__link", timeout=8000)
            except Exception:
                continue
            for anchor in pg.query_selector_all("a.job__link"):
                offer = _to_offer(anchor)
                if offer is not None:
                    offers.setdefault(offer.source_id, offer)
                if len(offers) >= max_results:
                    break
    return list(offers.values())[:max_results]
