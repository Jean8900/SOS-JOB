"""Connecteur Greenhouse (lot 1.5) : API publique par board, sans clé.
`content=true` renvoie la description en HTML échappé ; pas de type de contrat
exposé -> déduit du titre (voir ats.guess_contract_type)."""
from __future__ import annotations

import html

from .. import scraper
from ..offer import Offer
from . import ats, http

SOURCE = "greenhouse"
API_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def _fetch_board(name: str, token: str) -> list[Offer]:
    response = http.get(API_URL.format(token=token), params={"content": "true"})
    response.raise_for_status()
    offers = []
    for job in response.json().get("jobs", []):
        title = job.get("title") or ""
        url = job.get("absolute_url") or ""
        if not (title and url):
            continue
        offers.append(Offer(
            source=SOURCE,
            source_id=f"{token}-{job['id']}",
            url=url,
            url_canonique=url,
            title=title,
            company=name,
            location=(job.get("location") or {}).get("name") or "",
            contract_type=ats.guess_contract_type(title),
            description=scraper.html_to_text(html.unescape(job.get("content") or "")),
            posted_at=job.get("updated_at"),
        ))
    return offers


def fetch(max_results: int = 5) -> list[Offer]:
    return ats.collect(SOURCE, _fetch_board)
