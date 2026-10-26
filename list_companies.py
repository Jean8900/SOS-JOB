"""Scrape WTJ pour un métier donné et ouvre directement la page HTML générée
dans le navigateur (rendue, pas le code source).

Usage : python list_companies.py "Data Scientist"
        (sans argument -> utilise le premier métier de config/criteria.yaml)
"""
from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.company_finder import build_companies_page  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent


def default_query() -> str:
    criteria_path = REPO_ROOT / "config" / "criteria.yaml"
    with criteria_path.open("r", encoding="utf-8") as f:
        criteria = yaml.safe_load(f)
    professions = criteria.get("professions") or []
    if not professions:
        raise SystemExit("Aucun métier dans config/criteria.yaml et aucun argument fourni. "
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
