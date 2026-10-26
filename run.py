"""Orchestrateur MVP1 : scrape -> filtre -> TUI -> génère un CV PDF par offre cochée.

Usage : python run.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import cv_builder, matcher, scraper  # noqa: E402
from src.ui import run_selection_ui  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    companies_cfg = load_yaml(REPO_ROOT / "config" / "companies.yaml")
    criteria = load_yaml(REPO_ROOT / "config" / "criteria.yaml")
    language = companies_cfg.get("language", "fr")
    max_results = int(criteria.get("max_results", 100))

    print("=== 1/4 Collecte : entreprises suivies ===")
    followed_hits, errors = scraper.collect_followed_companies(companies_cfg["companies"], language)
    if errors:
        print(f"-> {len(errors)} entreprise(s) en échec (ignorées) : " + ", ".join(e["company"] for e in errors))

    print("=== 2/4 Collecte : recherche élargie ===")
    broad_hits: list[dict] = []
    if companies_cfg["companies"]:
        anchor_url = scraper.company_url(companies_cfg["companies"][0], language)
        try:
            anchor_config = scraper.get_company_jobs_config(anchor_url)
            query = matcher.search_query_from_criteria(criteria)
            broad_hits = scraper.fetch_broad_search_hits(anchor_config, query=query)
            print(f"-> {len(broad_hits)} offre(s) trouvées sur l'ensemble de WTJ pour: \"{query}\"")
        except (scraper.ScraperError, Exception) as exc:  # noqa: BLE001
            print(f"-> recherche élargie indisponible: {exc}")

    all_hits: dict[str, dict] = {}
    for hit in followed_hits + broad_hits:
        slug = hit.get("slug")
        if slug:
            all_hits.setdefault(slug, hit)
    print(f"-> {len(all_hits)} offre(s) uniques collectées au total")

    print("=== 3/4 Filtrage strict ===")
    coarse_filtered = matcher.filter_hits(list(all_hits.values()), criteria)
    print(f"-> {len(coarse_filtered)} offre(s) après filtre léger (lieu/contrat/métier)")

    jobs: list[dict] = []
    for hit in coarse_filtered[: max_results * 2]:  # marge avant le filtre fin
        company_slug = hit.get("_source_company_slug") or (hit.get("organization") or {}).get("slug")
        if not company_slug:
            continue
        try:
            job = scraper.fetch_job_detail(company_slug, hit["slug"])
            job["_company_slug"] = company_slug  # organization.slug est absent du détail -> on le propage depuis le hit
            jobs.append(job)
        except Exception as exc:  # noqa: BLE001
            print(f"[scraper] détail indisponible pour {hit.get('slug')}: {exc}")

    fine_filtered = matcher.filter_details(jobs, criteria)[:max_results]
    print(f"-> {len(fine_filtered)} offre(s) après filtre fin (stack/séniorité), affichées dans le tableau")

    if not fine_filtered:
        print("Aucune offre ne correspond à tes critères actuels (config/criteria.yaml).")
        return

    print("=== 4/4 Sélection ===")
    selected = run_selection_ui(fine_filtered)
    if not selected:
        print("Aucune offre cochée, aucun CV généré.")
        return

    print(f"=== Génération de {len(selected)} CV adapté(s) ===")
    for job in selected:
        company_slug = job.get("_company_slug") or (job.get("organization") or {}).get("slug", "entreprise")
        try:
            pdf_path = cv_builder.generate_cv_for_job(job, company_slug)
            print(f"OK  {job.get('name')} ({company_slug}) -> {pdf_path.relative_to(REPO_ROOT)}")
        except Exception as exc:  # noqa: BLE001
            print(f"ECHEC  {job.get('name')} ({company_slug}): {exc}")


if __name__ == "__main__":
    main()
