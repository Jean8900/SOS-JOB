"""Orchestrateur MVP1 : scrape -> filtre -> TUI -> génère CV + LM par offre cochée.

Usage : python run.py [all] [force]
  all    : saute la sélection TUI, prend toutes les offres filtrées
  force  : régénère les LM même si déjà présentes dans l'archive
           (sans ce suffixe : une LM déjà archivée n'est pas refaite)
Combinables : python run.py all force
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import config, cv_builder, lm_builder, matcher, scraper  # noqa: E402
from src.ui import run_selection_ui  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent


def main() -> None:
    args = {a.lower() for a in sys.argv[1:]}
    select_all = "all" in args
    force_lm = "force" in args

    companies_cfg = config.load_companies()
    criteria = config.load_criteria()
    language = companies_cfg.get("language", "fr")
    max_results = int(criteria.get("max_results", 100))
    followed_max_pages = int(criteria.get("followed_max_pages", 3))
    broad_max_pages = int(criteria.get("broad_search_max_pages", 2))
    anchor_slug = companies_cfg.get("anchor_company") or companies_cfg["companies"][0]

    print("=== 1/4 Collecte : entreprises suivies ===")
    followed_hits, errors = scraper.collect_followed_companies(companies_cfg["companies"], language, max_pages=followed_max_pages)
    if errors:
        print(f"-> {len(errors)} entreprise(s) en échec (ignorées) : " + ", ".join(e["company"] for e in errors))

    print("=== 2/4 Collecte : recherche élargie ===")
    broad_hits: list[dict] = []
    try:
        anchor_config = scraper.get_company_jobs_config(scraper.company_url(anchor_slug, language))
        query = matcher.search_query_from_criteria(criteria)
        broad_hits = scraper.fetch_broad_search_hits(anchor_config, query=query, max_pages=broad_max_pages)
        print(f"-> {len(broad_hits)} offre(s) trouvées sur l'ensemble de WTJ pour: \"{query}\"")
    except Exception as exc:  # noqa: BLE001
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
        print("Aucune offre ne correspond à tes critères actuels (input/criteria.yaml).")
        return

    print("=== 4/4 Sélection ===")
    if select_all:
        selected = fine_filtered
        print(f"-> suffixe 'all' : {len(selected)} offre(s) sélectionnée(s) automatiquement, pas de TUI")
    else:
        selected = run_selection_ui(fine_filtered)
    if not selected:
        print("Aucune offre cochée, aucun CV/LM généré.")
        return

    print(f"=== Génération de {len(selected)} CV adapté(s) ===")
    for job in selected:
        company_slug = job.get("_company_slug") or (job.get("organization") or {}).get("slug", "entreprise")
        try:
            pdf_path = cv_builder.generate_cv_for_job(job, company_slug)
            print(f"OK  {job.get('name')} ({company_slug}) -> {pdf_path.relative_to(REPO_ROOT)}")
        except Exception as exc:  # noqa: BLE001
            print(f"ECHEC  {job.get('name')} ({company_slug}): {exc}")

    print(f"=== Génération des LM ({'force' if force_lm else 'saute si déjà archivée'}) ===")
    for job in selected:
        company_slug = job.get("_company_slug") or (job.get("organization") or {}).get("slug", "entreprise")
        basename = lm_builder.basename_for_job(job, company_slug)
        if not force_lm and lm_builder.is_archived(basename):
            print(f"SKIP  {job.get('name')} ({company_slug}) -> déjà dans l'archive (utilise le suffixe 'force' pour refaire)")
            continue
        try:
            pdf_path = lm_builder.generate_lm_for_job(job, company_slug)
            print(f"OK  {job.get('name')} ({company_slug}) -> {pdf_path.relative_to(REPO_ROOT)}")
        except Exception as exc:  # noqa: BLE001
            print(f"ECHEC  {job.get('name')} ({company_slug}): {exc}")


if __name__ == "__main__":
    main()
