"""Recherche exhaustive (toutes les pages, aucun plafond) sur un métier donné,
sur l'ensemble de WTJ (pas restreint aux entreprises suivies), et génère une
page HTML listant les entreprises par ordre alphabétique avec un lien
cliquable vers la page jobs de chacune.
"""
from __future__ import annotations

from html import escape
from pathlib import Path
from urllib.parse import urlencode

from . import scraper

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output"


def _algolia_search_all(anchor_config: dict, query: str) -> tuple[dict[str, str], int]:
    """Pagine TOUTES les pages de résultats (pas de plafond). Retourne {slug: name} + nb d'offres."""
    app_id = anchor_config["algolia_app_id"]
    endpoint = f"https://{app_id.lower()}-dsn.algolia.net/1/indexes/*/queries"
    headers = {
        "X-Algolia-Application-Id": app_id,
        "X-Algolia-API-Key": anchor_config["algolia_api_key"],
        "Origin": anchor_config["origin"],
        "Referer": anchor_config["company_jobs_url"],
    }
    companies: dict[str, str] = {}
    page = 0
    nb_pages = 1
    total_hits = 0
    while page < nb_pages:
        payload = {"requests": [{
            "indexName": anchor_config["algolia_index_name"],
            "params": urlencode({"query": query, "hitsPerPage": 100, "page": page}),
        }]}
        result = scraper.fetch_json(endpoint, payload, headers)["results"][0]
        nb_pages = result["nbPages"]
        total_hits = result["nbHits"]
        for hit in result["hits"]:
            org = hit.get("organization") or {}
            slug, name = org.get("slug"), org.get("name")
            if slug and name:
                companies.setdefault(slug, name.strip())
        page += 1
    return companies, total_hits


def slugify_filename(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def build_companies_page(query: str, language: str = "fr", output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Scrape WTJ pour `query` (texte libre, ex: un métier) et écrit une page HTML
    listant, par ordre alphabétique, toutes les entreprises ayant au moins une
    offre correspondante -- avec un lien cliquable vers leur page jobs.
    Retourne le chemin du fichier généré.
    """
    anchor_config = scraper.get_company_jobs_config(scraper.company_url("illuin-tech", language))
    companies, total_hits = _algolia_search_all(anchor_config, query)
    sorted_items = sorted(companies.items(), key=lambda kv: kv[1].casefold())

    rows = "\n".join(
        f'    <li><a href="{escape(scraper.company_url(slug, language))}" target="_blank" rel="noopener">{escape(name)}</a></li>'
        for slug, name in sorted_items
    )
    html = f"""<!DOCTYPE html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<title>Entreprises -- {escape(query)}</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ font-size: 1.2rem; }}
  ul {{ line-height: 1.9; padding-left: 1.2rem; }}
  a {{ color: #1e325a; }}
</style>
</head>
<body>
<h1>{len(sorted_items)} entreprises -- recherche "{escape(query)}" ({total_hits} offres, WTJ)</h1>
<ul>
{rows}
</ul>
</body>
</html>
"""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"companies_{slugify_filename(query)}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path
