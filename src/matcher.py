"""Filtre strict des offres selon input/criteria.yaml, sur le schéma Offer
unique (voir src/offer.py) -- un seul passage, quelle que soit la source,
puisque chaque connecteur livre déjà un Offer complet (plus de split
hit/détail propre à WTJ)."""
from __future__ import annotations

from .offer import Offer


def _matches_any_keyword(text: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    text = text.lower()
    return any(keyword.lower() in text for keyword in keywords)


def filter_offers(offers: list[Offer], criteria: dict) -> list[Offer]:
    locations = criteria.get("locations") or []
    contract_types = [c.lower() for c in (criteria.get("contract_types") or [])]
    professions = criteria.get("professions") or []
    stack = criteria.get("stack") or []
    seniority = criteria.get("seniority") or []
    excluded_companies = criteria.get("excluded_companies") or []

    kept = []
    for offer in offers:
        if excluded_companies and _matches_any_keyword(offer.company, excluded_companies):
            continue
        if locations and not _matches_any_keyword(offer.location, locations):
            continue
        if contract_types and not _matches_any_keyword(offer.contract_type, contract_types):
            continue
        haystack_title = offer.title
        haystack_full = f"{offer.title} {offer.description}"
        if professions and not (_matches_any_keyword(haystack_title, professions) or _matches_any_keyword(haystack_full, professions)):
            continue
        if stack and not _matches_any_keyword(haystack_full, stack):
            continue
        if seniority and not _matches_any_keyword(haystack_full, seniority):
            continue
        kept.append(offer)
    return kept


def search_query_from_criteria(criteria: dict) -> str:
    keywords = list(criteria.get("professions") or []) + list(criteria.get("stack") or [])
    extra = criteria.get("search_query_extra") or ""
    if extra:
        keywords.append(extra)
    return " ".join(keywords)
