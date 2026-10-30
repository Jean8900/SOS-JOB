"""Connecteur Free-Work (www.free-work.com) -- job 1 (analyse) :

API JSON interne trouvée par déviné d'URL à partir du préfixe `/api/`
observé dans la page de recherche (`https://www.free-work.com/api/job_postings`,
format Hydra/API Platform). Pas d'anti-bot rencontré sur cette lecture GET.
Recherche globale par mot-clé -- pas besoin d'une liste d'entreprises connue.
"""
from __future__ import annotations

from .. import matcher, scraper
from ..offer import Offer
from . import http

SOURCE = "free_work"
API_URL = "https://www.free-work.com/api/job_postings"

_CONTRACT_MAP = {
    "permanent": "full_time",
    "contractor": "freelance",
    "internship": "internship",
    "apprenticeship": "apprenticeship",
    "temporary_worker": "temporary",
    "vie": "vie",
}


def _contract_type(posting: dict) -> str:
    return " ".join(_CONTRACT_MAP.get(c, c) for c in (posting.get("contracts") or []))


def _location(posting: dict) -> str:
    loc = posting.get("location") or {}
    label = loc.get("shortLabel") or loc.get("label") or ""
    if posting.get("remoteMode") in ("full", "partial"):
        label = f"{label} Remote".strip()
    return label


def _to_offer(posting: dict) -> Offer:
    job_slug = (posting.get("job") or {}).get("slug") or posting["slug"]
    posting_slug = posting["slug"]
    url = f"https://www.free-work.com/fr/tech-it/job-mission/{job_slug}/{posting_slug}"
    description = scraper.html_to_text(posting.get("description")) + " " + scraper.html_to_text(posting.get("candidateProfile"))
    company = (posting.get("company") or {}).get("name") or ""
    return Offer(
        source=SOURCE,
        source_id=str(posting.get("id") or posting_slug),
        url=url,
        url_canonique=url,
        title=posting.get("title") or "",
        company=company,
        location=_location(posting),
        contract_type=_contract_type(posting),
        description=description,
        posted_at=posting.get("publishedAt"),
    )


def fetch(max_results: int = 5) -> list[Offer]:
    from .. import config
    criteria = config.load_criteria()
    query = matcher.search_query_from_criteria(criteria)

    offers: list[Offer] = []
    page = 1
    while len(offers) < max_results and page <= 5:
        response = http.get(API_URL, params={"query": query, "page": page})
        response.raise_for_status()
        data = response.json()
        members = data.get("hydra:member") or []
        if not members:
            break
        for posting in members:
            offers.append(_to_offer(posting))
            if len(offers) >= max_results:
                break
        page += 1
    return offers
