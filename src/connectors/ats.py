"""Socle commun des connecteurs ATS (lot 1.5) : Greenhouse, Lever, Ashby.

Ces ATS n'ont pas de recherche globale, seulement une API publique par
entreprise (`board`). On découvre donc les entreprises à interroger :
1. entreprises WTJ ayant des offres pour chaque `discovery_queries`
   (input/ats_companies.yaml) ;
2. pour chacune, on teste quelques identifiants dérivés de son nom sur les
   trois ATS ; le résultat (trouvé ou non) est mis en cache dans
   output/ats_cache.json pour ne pas re-sonder à chaque run ;
3. les entrées manuelles de `companies:` priment sur tout ça.
"""
from __future__ import annotations

import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .. import config, scraper
from ..company_finder import _algolia_search_all
from ..offer import Offer
from . import http

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_PATH = REPO_ROOT / "output" / "ats_cache.json"
NEGATIVE_TTL = timedelta(days=30)
PROBE_THREADS = 4

_PROBE_URLS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
    "lever": "https://api.lever.co/v0/postings/{token}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{token}",
}

_resolved: dict[str, list[tuple[str, str]]] | None = None


def _ascii_lower(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def _candidate_tokens(wtj_slug: str, name: str) -> list[str]:
    # Pas de candidat "premier mot seul" : trop de faux positifs (ex. "Blue" -> Blue Light Card).
    cleaned = re.sub(r"\b(group|groupe|france|sas|sa|inc|ltd|technologies|technology)\b", "", _ascii_lower(name))
    words = re.findall(r"[a-z0-9]+", cleaned)
    base_slug = re.sub(r"-\d+$", "", wtj_slug)
    candidates = ["".join(words), "-".join(words), base_slug, base_slug.replace("-", "")]
    seen: set[str] = set()
    return [c for c in candidates if c and not (c in seen or seen.add(c))]


def _count_jobs(ats: str, payload) -> int:
    if ats == "lever":
        return len(payload) if isinstance(payload, list) else 0
    return len((payload or {}).get("jobs", [])) if isinstance(payload, dict) else 0


def _probe(token: str) -> dict[str, int]:
    found: dict[str, int] = {}
    for ats, url in _PROBE_URLS.items():
        try:
            response = http.SESSION.get(url.format(token=token), timeout=(10, 30))
            if response.status_code != 200:
                continue
            payload = response.json()
        except Exception:  # noqa: BLE001 -- un token qui ne répond pas = pas de board
            continue
        if ats == "lever" and not payload:
            continue
        found[ats] = _count_jobs(ats, payload)
    return found


def _discover(wtj_slug: str, name: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    for token in _candidate_tokens(wtj_slug, name):
        found = _probe(token)
        if found:
            ats = max(found, key=found.get)  # si plusieurs ATS (migration), le plus fourni
            return {"name": name, "ats": ats, "token": token, "jobs": found[ats], "checked_at": now}
    return {"name": name, "ats": None, "token": None, "jobs": 0, "checked_at": now}


def _load_cache() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _expired_negative(entry: dict) -> bool:
    if entry.get("ats"):
        return False
    return datetime.now(timezone.utc) - datetime.fromisoformat(entry["checked_at"]) > NEGATIVE_TTL


def _wtj_companies(queries: list[str]) -> dict[str, str]:
    cfg = config.load_companies()
    language = cfg.get("language", "fr")
    anchor_slug = cfg.get("anchor_company") or cfg["companies"][0]
    anchor_config = scraper.get_company_jobs_config(scraper.company_url(anchor_slug, language))
    companies: dict[str, str] = {}
    for query in queries:
        found, _ = _algolia_search_all(anchor_config, query)
        companies.update(found)
    return companies


def resolve_boards() -> dict[str, list[tuple[str, str]]]:
    """{ats: [(nom entreprise, token), ...]} -- découverte + cache + entrées manuelles."""
    global _resolved
    if _resolved is not None:
        return _resolved

    cfg = config.load_ats_companies()
    cache = _load_cache()
    wtj = _wtj_companies(list(cfg.get("discovery_queries") or []))

    to_probe = [(slug, name) for slug, name in wtj.items() if slug not in cache or _expired_negative(cache[slug])]
    if to_probe:
        print(f"[ats] découverte : {len(to_probe)} entreprise(s) à sonder sur Greenhouse/Lever/Ashby (une seule fois, mis en cache)")
        with ThreadPoolExecutor(PROBE_THREADS) as pool:
            for (slug, _), entry in zip(to_probe, pool.map(lambda sn: _discover(*sn), to_probe)):
                cache[slug] = entry
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")

    manual = {(c["ats"], c["token"]): c["name"] for c in (cfg.get("companies") or [])}
    boards: dict[str, dict[str, str]] = {ats: {} for ats in _PROBE_URLS}
    for slug in wtj:
        entry = cache.get(slug) or {}
        if entry.get("ats") and entry.get("jobs"):
            boards[entry["ats"]][entry["token"]] = entry["name"]
    for (ats, token), name in manual.items():
        boards[ats][token] = name

    _resolved = {ats: [(name, token) for token, name in tokens.items()] for ats, tokens in boards.items()}
    return _resolved


def guess_contract_type(title: str, declared: str = "") -> str:
    """Normalise le type de contrat. Si l'ATS n'en donne pas (Greenhouse), on déduit du titre :
    stage/alternance sinon CDI -- les ATS d'entreprises tech listent surtout du CDI."""
    declared = (declared or "").lower().replace("-", "").replace("_", "").replace(" ", "")
    mapping = {
        "fulltime": "full_time", "cdi": "full_time", "permanent": "full_time",
        "parttime": "part_time", "intern": "internship", "internship": "internship", "stage": "internship",
        "contract": "temporary", "temporary": "temporary", "cdd": "temporary",
        "apprenticeship": "apprenticeship", "alternance": "apprenticeship",
    }
    if declared in mapping:
        return mapping[declared]
    lowered = title.lower()
    if re.search(r"\b(intern|internship|stage|stagiaire)\b", lowered):
        return "internship"
    if re.search(r"\b(alternance|apprenti|apprentice|apprenticeship)\b", lowered):
        return "apprenticeship"
    return "full_time"


def _rank(offers: list[Offer], professions: list[str]) -> list[Offer]:
    keywords = [p.lower() for p in professions]
    return sorted(offers, key=lambda o: not any(k in o.title.lower() for k in keywords))


def collect(ats: str, fetch_board) -> list[Offer]:
    """`fetch_board(name, token) -> list[Offer]` fourni par le connecteur de l'ATS.
    Une entreprise en échec est loggée et ignorée, les autres continuent."""
    cfg = config.load_ats_companies()
    limit = int(cfg.get("max_offers_per_company", 5))
    professions = list(config.load_criteria().get("professions") or [])

    offers: list[Offer] = []
    for name, token in resolve_boards()[ats]:
        try:
            company_offers = fetch_board(name, token)
        except Exception as exc:  # noqa: BLE001
            print(f"[{ats}] {name}: ECHEC -- {exc}")
            continue
        offers.extend(_rank(company_offers, professions)[:limit])
    return offers
