"""Collecte des offres Welcome to the Jungle : liste d'entreprises suivies + recherche élargie.

Basé sur le MVP1 (notebook wtj_offer_reader.ipynb), généralisé pour boucler sur
plusieurs entreprises et interroger l'index Algolia global sans filtre
organisation (recherche élargie par mots-clés).
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from urllib.parse import urlencode, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.mount("https://", HTTPAdapter(max_retries=Retry(
    total=2, status_forcelist=[429, 502, 503, 504],
    allowed_methods=["GET", "POST"],
)))


class ScraperError(Exception):
    """Erreur de scraping, avec le nom de l'entreprise concernée quand c'est pertinent."""


def fetch_json(url: str, payload: dict | None = None, extra_headers: dict | None = None) -> dict:
    response = SESSION.request(
        "POST" if payload is not None else "GET",
        url, json=payload, headers=extra_headers, timeout=(10, 30),
    )
    response.raise_for_status()
    return response.json()


def _find_jobs_search_properties(node):
    if isinstance(node, dict):
        properties = node.get("properties")
        if node.get("kind") == "jobs-search" and isinstance(properties, dict) and properties.get("algolia_api_key"):
            return properties
        for value in node.values():
            found = _find_jobs_search_properties(value)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_jobs_search_properties(item)
            if found is not None:
                return found
    return None


def get_company_jobs_config(company_jobs_url: str) -> dict:
    parsed = urlparse(company_jobs_url)
    path = parsed.path.rstrip("/").replace("/companies-v1/", "/companies/")
    if not re.fullmatch(r"/[^/]+/companies/[^/]+/jobs", path):
        raise ValueError("URL attendue: une page entreprise /companies[/ -v1]/.../jobs.")
    try:
        page_payload = fetch_json(
            "https://api.welcometothejungle.com/api/v1/pages?" + urlencode({"path": path})
        )
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise ScraperError(f"page jobs introuvable (404) pour {company_jobs_url}") from exc
        raise ScraperError(f"HTTP {exc.response.status_code if exc.response is not None else '?'} sur {company_jobs_url}") from exc
    jobs_search = _find_jobs_search_properties(page_payload)
    if not jobs_search:
        raise ScraperError(f"configuration jobs-search absente pour {company_jobs_url}")
    return {
        "company_slug": jobs_search["website_organization"]["slug"],
        "filters": jobs_search["filters"],
        "default_job": jobs_search.get("default_job"),
        "algolia_api_key": jobs_search["algolia_api_key"],
        "algolia_index_name": jobs_search["algolia_index_name"],
        "algolia_app_id": jobs_search["algolia_app_id"],
        "company_jobs_url": company_jobs_url,
        "origin": f"{parsed.scheme}://{parsed.netloc}",
    }


def _build_algolia_filters(filters: dict) -> str:
    parts = []
    for key, values in filters.items():
        values = values if isinstance(values, list) else [values]
        alternatives = [f"{key}:{json.dumps(value)}" for value in values]
        if alternatives:
            parts.append("(" + " OR ".join(alternatives) + ")")
    return " AND ".join(parts)


def _algolia_search(config: dict, query: str = "", filters: str = "", hits_per_page: int = 100, max_pages: int = 3) -> list[dict]:
    app_id = config["algolia_app_id"]
    endpoint = f"https://{app_id.lower()}-dsn.algolia.net/1/indexes/*/queries"
    headers = {
        "X-Algolia-Application-Id": app_id,
        "X-Algolia-API-Key": config["algolia_api_key"],
        "Origin": config["origin"],
        "Referer": config["company_jobs_url"],
    }
    hits = []
    page = 0
    while page < max_pages:
        payload = {"requests": [{
            "indexName": config["algolia_index_name"],
            "params": urlencode({
                "query": query, "filters": filters,
                "hitsPerPage": hits_per_page, "page": page,
            }),
        }]}
        result = fetch_json(endpoint, payload, headers)["results"][0]
        if "hits" not in result:
            raise ScraperError(f"recherche Algolia impossible: {result.get('message', result)}")
        hits.extend(result["hits"])
        page += 1
        if page >= result["nbPages"]:
            break
    return hits


def fetch_job_hits(config: dict) -> list[dict]:
    """Toutes les offres d'une entreprise (page jobs de l'entreprise)."""
    hits = _algolia_search(config, filters=_build_algolia_filters(config["filters"]))
    default_job = config.get("default_job") or {}
    if default_job.get("slug"):
        hits.append(default_job)
    unique_hits = {}
    for hit in hits:
        if hit.get("slug"):
            unique_hits.setdefault(hit["slug"], hit)
    return list(unique_hits.values())


def fetch_broad_search_hits(anchor_config: dict, query: str, extra_filters: str = "", hits_per_page: int = 100, max_pages: int = 2) -> list[dict]:
    """Recherche élargie : même index Algolia, sans filtre organisation.

    `anchor_config` = la config jobs-search récupérée via get_company_jobs_config()
    pour N'IMPORTE QUELLE entreprise (sert juste à récupérer les identifiants Algolia).
    """
    hits = _algolia_search(anchor_config, query=query, filters=extra_filters, hits_per_page=hits_per_page, max_pages=max_pages)
    unique_hits = {}
    for hit in hits:
        if hit.get("slug"):
            unique_hits.setdefault(hit["slug"], hit)
    return list(unique_hits.values())


def fetch_job_detail(company_slug: str, job_slug: str) -> dict:
    return fetch_json(
        f"https://api.welcometothejungle.com/api/v1/organizations/{company_slug}/jobs/{job_slug}"
    )["job"]


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self.parts)


def html_to_text(raw_html) -> str:
    if not raw_html:
        return ""
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
    parser = _TextExtractor()
    parser.feed(cleaned)
    return re.sub(r"\s+", " ", parser.get_text()).strip()


def company_url(slug: str, language: str = "fr") -> str:
    return f"https://www.welcometothejungle.com/{language}/companies-v1/{slug}/jobs"


def collect_followed_companies(slugs: list[str], language: str = "fr") -> tuple[list[dict], list[dict]]:
    """Scrape la liste d'entreprises suivies.

    Debug minimaliste : une entreprise qui échoue n'interrompt pas les autres ;
    l'erreur est collectée et renvoyée séparément pour affichage.
    Retourne (hits, erreurs) où chaque hit porte en plus "_source_company_slug".
    """
    all_hits: list[dict] = []
    errors: list[dict] = []
    for slug in slugs:
        url = company_url(slug, language)
        try:
            config = get_company_jobs_config(url)
            hits = fetch_job_hits(config)
        except (ScraperError, requests.RequestException, ValueError, KeyError) as exc:
            errors.append({"company": slug, "error": str(exc)})
            print(f"[scraper] {slug}: ECHEC -- {exc}")
            continue
        for hit in hits:
            hit["_source_company_slug"] = config["company_slug"]
        all_hits.extend(hits)
        print(f"[scraper] {slug}: OK -- {len(hits)} offre(s)")
    return all_hits, errors
