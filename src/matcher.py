"""Filtre strict des offres selon config/criteria.yaml.

Deux passes, pour limiter le nombre d'appels à l'API détail :
1. filter_hits   : filtre léger sur les champs déjà présents dans les résultats
                    de recherche (localisation, remote, contrat, métier).
2. filter_details: filtre fin sur la description complète (stack, séniorité),
                    appelé uniquement sur les offres déjà retenues en étape 1.
"""
from __future__ import annotations

from . import scraper


def _profession_text(hit_or_job: dict) -> str:
    profession = hit_or_job.get("profession") or {}
    names = []
    for key in ("category_name", "sub_category_name", "name"):
        value = profession.get(key)
        if isinstance(value, dict):
            names.append(value.get("fr") or value.get("en") or "")
        elif isinstance(value, str):
            names.append(value)
    return " ".join(names).lower()


def _locations_text(hit_or_job: dict) -> str:
    offices = hit_or_job.get("offices") or ([hit_or_job["office"]] if hit_or_job.get("office") else [])
    parts = []
    for office in offices:
        if not office:
            continue
        parts.append(str(office.get("city") or ""))
        parts.append(str(office.get("state") or ""))
        parts.append(str(office.get("address") or ""))
    return " ".join(parts).lower()


def _matches_any_keyword(text: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    text = text.lower()
    return any(keyword.lower() in text for keyword in keywords)


def filter_hits(hits: list[dict], criteria: dict) -> list[dict]:
    locations = criteria.get("locations") or []
    remote_wanted = criteria.get("remote")
    contract_types = [c.lower() for c in (criteria.get("contract_types") or [])]
    professions = criteria.get("professions") or []

    kept = []
    for hit in hits:
        if locations:
            loc_text = _locations_text(hit)
            is_remote_match = "remote" in [l.lower() for l in locations] and hit.get("remote") in ("full", "partial")
            if not _matches_any_keyword(loc_text, [l for l in locations if l.lower() != "remote"]) and not is_remote_match:
                continue
        if remote_wanted and hit.get("remote") != remote_wanted:
            continue
        if contract_types and str(hit.get("contract_type", "")).lower() not in contract_types:
            continue
        if professions and not _matches_any_keyword(_profession_text(hit) + " " + str(hit.get("name", "")), professions):
            continue
        kept.append(hit)
    return kept


def filter_details(jobs: list[dict], criteria: dict) -> list[dict]:
    stack = criteria.get("stack") or []
    seniority = criteria.get("seniority") or []
    if not stack and not seniority:
        return jobs

    kept = []
    for job in jobs:
        haystack = " ".join([
            str(job.get("name", "")),
            scraper.html_to_text(job.get("description")),
            scraper.html_to_text(job.get("profile")),
        ])
        if not _matches_any_keyword(haystack, stack):
            continue
        if not _matches_any_keyword(haystack, seniority):
            continue
        kept.append(job)
    return kept


def search_query_from_criteria(criteria: dict) -> str:
    keywords = list(criteria.get("professions") or []) + list(criteria.get("stack") or [])
    extra = criteria.get("search_query_extra") or ""
    if extra:
        keywords.append(extra)
    return " ".join(keywords)
