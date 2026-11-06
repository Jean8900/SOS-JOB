"""Connecteur Welcome to the Jungle : entreprises suivies + recherche élargie.

Toute la logique de scraping bas niveau reste dans src/scraper.py --
ce module se contente de la convertir en Offer, pour que le reste du pipeline
ne reparle plus jamais la forme brute WTJ.
"""
from __future__ import annotations

from .. import config, matcher, scraper
from ..offer import Offer

SOURCE = "welcome_to_the_jungle"


def _to_offer(job: dict, company_slug: str) -> Offer:
    offices = job.get("offices") or ([job["office"]] if job.get("office") else [])
    city = next((o.get("city") for o in offices if o and o.get("city")), None)
    location = city or ("Remote" if job.get("remote") in ("full", "partial") else "")
    org = job.get("organization") or {}
    slug = job.get("slug") or str(job.get("id") or "")
    return Offer(
        source=SOURCE,
        source_id=slug,
        url=f"https://www.welcometothejungle.com/fr/companies/{company_slug}/jobs/{slug}",
        url_canonique=f"https://www.welcometothejungle.com/fr/companies/{company_slug}/jobs/{slug}",
        title=job.get("name") or "",
        company=org.get("name") or company_slug,
        location=location,
        contract_type=str(job.get("contract_type") or ""),
        description=scraper.html_to_text(job.get("description")) + " " + scraper.html_to_text(job.get("profile")),
        posted_at=job.get("published_at"),
    )


def fetch(max_results: int = 5) -> list[Offer]:
    companies_cfg = config.load_companies()
    criteria = config.load_criteria()
    language = companies_cfg.get("language", "fr")
    followed_max_pages = int(criteria.get("followed_max_pages", 3))
    broad_max_pages = int(criteria.get("broad_search_max_pages", 2))
    anchor_slug = companies_cfg.get("anchor_company") or companies_cfg["companies"][0]

    followed_hits, _errors = scraper.collect_followed_companies(companies_cfg["companies"], language, max_pages=followed_max_pages)

    broad_hits: list[dict] = []
    try:
        anchor_config = scraper.get_company_jobs_config(scraper.company_url(anchor_slug, language))
        query = matcher.search_query_from_criteria(criteria)
        broad_hits = scraper.fetch_broad_search_hits(anchor_config, query=query, max_pages=broad_max_pages)
    except Exception as exc:  # noqa: BLE001 -- une recherche élargie indisponible ne doit pas bloquer les entreprises suivies
        print(f"[wtj] recherche élargie : ECHEC -- {exc}")

    unique: dict[str, dict] = {}
    for hit in followed_hits + broad_hits:
        slug = hit.get("slug")
        if slug:
            unique.setdefault(slug, hit)

    offers: list[Offer] = []
    # Les entreprises suivies arrivent en tête par centaines : on lit d'abord les offres dont le titre vise un métier cherché.
    keywords = [p.lower() for p in criteria.get("professions") or []]
    ranked = sorted(unique.values(), key=lambda h: not any(k in (h.get("name") or "").lower() for k in keywords))
    integrated_only = criteria.get("integrated_apply_only")  # go.py : seules ces offres ont un formulaire sur WTJ, les autres renvoient chez l'employeur
    for hit in ranked[: max_results * (8 if integrated_only else 3)]:
        company_slug = hit.get("_source_company_slug") or (hit.get("organization") or {}).get("slug")
        if not company_slug:
            continue
        try:
            job = scraper.fetch_job_detail(company_slug, hit["slug"])
        except Exception as exc:  # noqa: BLE001 -- une offre illisible n'arrête pas les autres
            print(f"[wtj] {company_slug}/{hit['slug']} : ECHEC -- {exc}")
            continue
        if integrated_only and job.get("ats") != "wkit":
            continue
        offers.append(_to_offer(job, company_slug))
        if len(offers) >= max_results:
            break
    return offers
