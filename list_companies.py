"""Scrape WTJ pour un métier donné et ouvre directement la page HTML générée
dans le navigateur (rendue, pas le code source).

Usage : python list_companies.py "Data Scientist"
        (sans argument -> utilise le premier métier de input/criteria.yaml)
"""
from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import config  # noqa: E402
from src.company_finder import build_companies_page  # noqa: E402


def default_query() -> str:
    professions = config.load_criteria().get("professions") or []
    if not professions:
        raise SystemExit("Aucun métier dans input/criteria.yaml et aucun argument fourni. "
                          "Usage: python list_companies.py \"Data Scientist\"")
    return professions[0]


def main() -> None:
    query = sys.argv[1] if len(sys.argv) > 1 else default_query()
    print(f"Recherche WTJ pour : \"{query}\" (toutes entreprises, pas de plafond)...")
    out_path = build_companies_page(query)
    print(f"{out_path.name} généré -> ouverture dans le navigateur...")
    webbrowser.open(out_path.resolve().as_uri())


if __name__ == "__main__":
    main()
