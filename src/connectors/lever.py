"""Connecteur Lever (lot 1.5) : API publique par entreprise, sans clé."""
from __future__ import annotations

from datetime import datetime, timezone

from ..offer import Offer
from . import ats, http

SOURCE = "lever"
API_URL = "https://api.lever.co/v0/postings/{token}"


def _location(posting: dict) -> str:
    categories = posting.get("categories") or {}
    parts = [categories.get("location") or "", *(categories.get("allLocations") or [])]
    if posting.get("workplaceType") == "remote":
        parts.append("Remote")
    return " / ".join(dict.fromkeys(p for p in parts if p))


def _fetch_board(name: str, token: str) -> list[Offer]:
    response = http.get(API_URL.format(token=token), params={"mode": "json"})
    response.raise_for_status()
    offers = []
    for posting in response.json():
        title = posting.get("text") or ""
        url = posting.get("hostedUrl") or ""
        if not (title and url):
            continue
        created = posting.get("createdAt")
        offers.append(Offer(
            source=SOURCE,
            source_id=f"{token}-{posting['id']}",
            url=url,
            url_canonique=url,
            title=title,
            company=name,
            location=_location(posting),
            contract_type=ats.guess_contract_type(title, (posting.get("categories") or {}).get("commitment") or ""),
            description=posting.get("descriptionPlain") or "",
            posted_at=datetime.fromtimestamp(created / 1000, timezone.utc).isoformat() if created else None,
        ))
    return offers


def fetch(max_results: int = 5) -> list[Offer]:
    return ats.collect(SOURCE, _fetch_board)
