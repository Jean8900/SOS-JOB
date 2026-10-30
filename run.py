"""Orchestrateur multi-sources : collecte (tous les sites actifs, ou choisis) ->
filtre -> TUI -> génère CV + LM par offre cochée.

Usage : python run.py [sites] [all] [force]
  sites  : liste à cocher pour choisir les sites à interroger
           (sans ce suffixe : tous les sites `enabled: true` de input/sites.yaml)
  all    : saute la sélection TUI des offres, prend toutes les offres filtrées
  force  : régénère les LM même si déjà présentes dans l'archive
           (sans ce suffixe : une LM déjà archivée n'est pas refaite)
Combinables, dans n'importe quel ordre : python run.py sites all force
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import applications, config, cv_builder, lm_builder, matcher  # noqa: E402
from src.offer import Offer  # noqa: E402
from src.ui import run_selection_ui, run_site_selection_ui  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent


def _load_connector(slug: str):
    return importlib.import_module(f"src.connectors.{slug}")


def _collect(sites: list[dict], max_results_per_site: int) -> list[Offer]:
    offers: list[Offer] = []
    for site in sites:
        try:
            connector = _load_connector(site["slug"])
            site_offers = connector.fetch(max_results=max_results_per_site)
            print(f"-> {site['name']}: {len(site_offers)} offre(s)")
            offers.extend(site_offers)
        except Exception as exc:  # noqa: BLE001 -- un site en échec ne bloque pas les autres
            print(f"-> {site['name']}: ECHEC -- {exc}")
    return offers


def main() -> None:
    args = {a.lower() for a in sys.argv[1:]}
    select_all = "all" in args
    force_lm = "force" in args
    choose_sites = "sites" in args

    sites_cfg = config.load_sites()
    all_sites = sites_cfg["sites"]
    max_results_per_site = int(sites_cfg.get("max_results_per_site", 5))

    if choose_sites:
        print("=== Choix des sites ===")
        chosen = run_site_selection_ui(all_sites)
        if not chosen:
            print("Aucun site choisi, arrêt.")
            return
    else:
        chosen = [s for s in all_sites if s.get("enabled")]
        if not chosen:
            print("Aucun site actif dans input/sites.yaml (ou utilise le suffixe 'sites').")
            return

    print("=== 1/4 Collecte : " + ", ".join(s["name"] for s in chosen) + " ===")
    offers = _collect(chosen, max_results_per_site)
    print(f"-> {len(offers)} offre(s) collectées au total")

    print("=== 2/4 Filtrage (input/criteria.yaml) ===")
    criteria = config.load_criteria()
    max_results = int(criteria.get("max_results", 100))
    filtered = matcher.filter_offers(offers, criteria)[:max_results]
    print(f"-> {len(filtered)} offre(s) après filtre")

    if not filtered:
        print("Aucune offre ne correspond à tes critères actuels (input/criteria.yaml).")
        return

    print("=== 3/4 Sélection ===")
    if select_all:
        selected = filtered
        print(f"-> suffixe 'all' : {len(selected)} offre(s) sélectionnée(s) automatiquement, pas de TUI")
    else:
        selected = run_selection_ui(filtered)
    if not selected:
        print("Aucune offre cochée, aucun CV/LM généré.")
        return

    print(f"=== 4/4 Génération de {len(selected)} CV adapté(s) ===")
    for offer in selected:
        try:
            pdf_path = cv_builder.generate_cv_for_job(offer)
            print(f"OK  {offer.title} ({offer.source}/{offer.company}) -> {pdf_path.relative_to(REPO_ROOT)}")
        except Exception as exc:  # noqa: BLE001
            print(f"ECHEC  {offer.title} ({offer.source}/{offer.company}): {exc}")

    print(f"=== Génération des LM ({'force' if force_lm else 'saute si déjà archivée'}) ===")
    for offer in selected:
        if not force_lm and lm_builder.is_archived(offer):
            print(f"SKIP  {offer.title} ({offer.source}/{offer.company}) -> déjà dans l'archive (suffixe 'force' pour refaire)")
            continue
        try:
            pdf_path = lm_builder.generate_lm_for_job(offer)
            print(f"OK  {offer.title} ({offer.source}/{offer.company}) -> {pdf_path.relative_to(REPO_ROOT)}")
        except Exception as exc:  # noqa: BLE001
            print(f"ECHEC  {offer.title} ({offer.source}/{offer.company}): {exc}")

    added = applications.register(selected)
    print(f"=== {added} offre(s) ajoutée(s) au copilot -> .\\apply.ps1 pour candidater ===")


if __name__ == "__main__":
    main()
