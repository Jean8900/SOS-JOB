"""Connecteur Inria (jobs.inria.fr) -- job 1 (analyse) :

Employeur unique (pas de liste d'entreprises à construire). Pas d'API JSON :
page HTML server-rendue (vieille stack jQuery/Bootstrap 3), recherche en
POST avec jeton CSRF Symfony lié à la session -- il faut donc une
requests.Session (GET pour récupérer cookie+jeton, puis POST avec les deux)
pour que le mot-clé soit réellement appliqué côté serveur (vérifié : sans
session, le filtre est silencieusement ignoré et renvoie tout).

Pas de description dans le listing (nécessiterait une requête par offre) --
limite connue, acceptable pour l'instant (voir TODO).
"""
from __future__ import annotations

import re

from ..offer import Offer
from . import http

SOURCE = "inria"
BASE_URL = "https://jobs.inria.fr"
LIST_URL = f"{BASE_URL}/public/classic/fr/offres"

_CARD_RE = re.compile(
    r'id="offre-desc-(?P<ref>[^"]+)".*?'
    r'href="(?P<path>/public/classic/fr/offres/[^"]+)"[^>]*title="(?P<title>[^"]*)"'
    r'.*?Ville</b>\s*:\s*(?P<ville>[^<]+)<',
    re.DOTALL,
)


def _to_offer(match: re.Match) -> Offer:
    url = BASE_URL + match["path"]
    title = re.sub(r"\s+", " ", match["title"]).replace(" - Nouvelle fenêtre", "").strip()
    return Offer(
        source=SOURCE,
        source_id=match["ref"],
        url=url,
        url_canonique=url,
        title=title,
        company="Inria",
        location=match["ville"].strip(),
        contract_type="",
        description="",
    )


def _search(keyword: str) -> str:
    """Une requête = une session (le jeton CSRF est lié à la session)."""
    session_get = http.get(LIST_URL)
    session_get.raise_for_status()
    token_match = re.search(r'name="recherche_offre\[_token\]" value="([^"]+)"', session_get.text)
    if not token_match:
        raise RuntimeError("jeton CSRF introuvable sur la page de recherche Inria -- le site a peut-être changé.")

    response = http.post(LIST_URL, data={
        "recherche_offre[motsClef]": keyword,
        "recherche_offre[_token]": token_match.group(1),
    })
    response.raise_for_status()
    return response.text


def fetch(max_results: int = 5) -> list[Offer]:
    """Le champ de recherche Inria traite la requête comme une phrase (AND) --
    envoyer tous les mots-clés concaténés donne 0 résultat. On essaie donc les
    mots-clés un par un (professions puis stack) jusqu'à atteindre max_results."""
    from .. import config
    criteria = config.load_criteria()
    keywords = list(criteria.get("professions") or []) + list(criteria.get("stack") or [])

    offers: dict[str, Offer] = {}
    for keyword in keywords:
        if len(offers) >= max_results:
            break
        html = _search(keyword)
        for match in _CARD_RE.finditer(html):
            offer = _to_offer(match)
            offers.setdefault(offer.source_id, offer)
            if len(offers) >= max_results:
                break
    return list(offers.values())[:max_results]
