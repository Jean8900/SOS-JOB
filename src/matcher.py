"""Filtre strict des offres selon input/criteria.yaml, sur le schéma Offer
unique (voir src/offer.py) -- un seul passage, quelle que soit la source,
puisque chaque connecteur livre déjà un Offer complet (plus de split
hit/détail propre à WTJ)."""
from __future__ import annotations

import re

from .offer import Offer

# « 3 ans », « 3 à 5 ans », « 5+ years » : retenu seulement si « expérience » est tout près (pas « fondée il y a 10 ans »).
_YEARS = re.compile(r"(?<![\w.,/+])(\+\s*)?(\d{1,2})(?:\s*(?:à|a|-|–|to)\s*(\d{1,2}))?\s*(\+)?\s*(?:ans?|années?|years?|yrs?)\b", re.I)
_EXPERIENCE = re.compile(r"exp[ée]rien|\bexp\b|\bxp\b", re.I)
_OPEN_BEFORE = re.compile(r"(minimum|\bmin\b|au moins|plus de|at least|\bover\b)\W*$", re.I)
_OPEN_AFTER = re.compile(r"^\W*(minimum|min\b|et plus|ou plus|or more|at least)", re.I)
_COMPANY_CLAIM = re.compile(r"\b(forte?|riche|nous|notre|depuis)\b", re.I)
MAX_PLAUSIBLE_YEARS = 15  # au-delà, c'est l'ancienneté de l'entreprise (« 20 ans d'expérience »), pas une exigence


def _matches_any_keyword(text: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    text = text.lower()
    return any(keyword.lower() in text for keyword in keywords)


def required_years(text: str) -> tuple[int, int | None] | None:
    """Années d'expérience demandées par une offre (recherche par motif, sans Claude) : (min, max), max None = sans plafond,
    None = l'offre n'en dit rien. Plusieurs mentions (« 5 ans en Python, 2 en Docker ») : la plus exigeante."""
    best = None
    for match in _YEARS.finditer(text):
        before, after = text[max(0, match.start() - 40):match.start()], text[match.end():match.end() + 40]
        if not (_EXPERIENCE.search(before) or _EXPERIENCE.search(after)) or _COMPANY_CLAIM.search(before):
            continue
        low = int(match.group(2))
        if low > MAX_PLAUSIBLE_YEARS:
            continue
        high = int(match.group(3)) if match.group(3) else low
        if match.group(1) or match.group(4) or _OPEN_BEFORE.search(before) or _OPEN_AFTER.search(after):
            high = None
        if best is None or low > best[0]:
            best = (low, high)
    return best


def years_match(text: str, years_min: int | None, years_max: int | None) -> bool:
    """La plage demandée par l'offre croise-t-elle la plage voulue ? Une offre qui ne dit rien est gardée."""
    if years_min is None and years_max is None:
        return True
    required = required_years(text)
    if required is None:
        return True
    low, high = required
    if years_max is not None and low > years_max:
        return False
    return not (years_min is not None and high is not None and high < years_min)


def filter_offers(offers: list[Offer], criteria: dict) -> list[Offer]:
    excluded_companies = criteria.get("excluded_companies") or []
    if criteria.get("disable_filters"):
        # Même sans filtre, les entreprises exclues (ex. ton employeur actuel) ne ressortent jamais.
        return [o for o in offers if not _matches_any_keyword(o.company, excluded_companies)] if excluded_companies else list(offers)
    locations = criteria.get("locations") or []
    contract_types = [c.lower() for c in (criteria.get("contract_types") or [])]
    professions = criteria.get("professions") or []
    stack = criteria.get("stack") or []
    years_min, years_max = criteria.get("years_min"), criteria.get("years_max")

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
        if not years_match(haystack_full, years_min, years_max):
            continue
        kept.append(offer)
    return kept


def search_query_from_criteria(criteria: dict) -> str:
    keywords = list(criteria.get("professions") or []) + list(criteria.get("stack") or [])
    extra = criteria.get("search_query_extra") or ""
    if extra:
        keywords.append(extra)
    return " ".join(keywords)
