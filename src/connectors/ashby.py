"""Connecteur Ashby (lot 1.5) : API publique par job board, sans clé."""
from __future__ import annotations

from ..offer import Offer
from . import ats, http

SOURCE = "ashby"
API_URL = "https://api.ashbyhq.com/posting-api/job-board/{token}"


def _fetch_board(name: str, token: str) -> list[Offer]:
    response = http.get(API_URL.format(token=token))
    response.raise_for_status()
    offers = []
    for job in response.json().get("jobs", []):
        title = job.get("title") or ""
        url = job.get("jobUrl") or ""
        if not (title and url) or job.get("isListed") is False:
            continue
        location = job.get("location") or ""
        if job.get("isRemote"):
            location = f"{location} Remote".strip()
        offers.append(Offer(
            source=SOURCE,
            source_id=f"{token}-{job['id']}",
            url=url,
            url_canonique=url,
            title=title,
            company=name,
            location=location,
            contract_type=ats.guess_contract_type(title, job.get("employmentType") or ""),
            description=job.get("descriptionPlain") or "",
            posted_at=job.get("publishedAt"),
        ))
    return offers


def fetch(max_results: int = 5) -> list[Offer]:
    return ats.collect(SOURCE, _fetch_board)
