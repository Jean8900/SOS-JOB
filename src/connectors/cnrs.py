"""Connecteur CNRS (emploi.cnrs.fr) -- job 1 (analyse) :

Employeur unique. Page HTML server-rendue (pas de __VIEWSTATE malgré
l'extension .aspx -- ni classique ASP.NET WebForms postback, un simple POST
direct sur Recherche.aspx avec le champ `InputSearchBy` suffit, vérifié par
comparaison du nombre de résultats avec/sans mot-clé). `/Offres/` (sans page
précise) renvoie un 403 IIS -- ce n'est pas un pare-feu anti-bot, juste
l'URL de recherche réelle qui est `/Offres/Recherche.aspx`.
"""
from __future__ import annotations

import re

from ..offer import Offer
from . import http

SOURCE = "cnrs"
BASE_URL = "https://emploi.cnrs.fr"
SEARCH_URL = f"{BASE_URL}/Offres/Recherche.aspx"

_CARD_RE = re.compile(
    r'<a href="(?P<path>/Offres/[^"]+)">(?P<title>[^<]+)</a></h3>.*?'
    r'<strong>(?P<lab>[^<]*)</strong>.*?'
    r'<p>(?P<location>[^<]*)</p>.*?'
    r'<span>(?P<contract>[^<]*)</span>',
    re.DOTALL,
)


def _to_offer(match: re.Match) -> Offer:
    url = BASE_URL + match["path"]
    source_id = match["path"].strip("/").split("/")[-2] if "/" in match["path"].strip("/") else match["path"]
    return Offer(
        source=SOURCE,
        source_id=source_id,
        url=url,
        url_canonique=url,
        title=match["title"].strip(),
        company=(match["lab"].strip() or "CNRS"),
        location=match["location"].strip(),
        contract_type=match["contract"].strip(),
        description="",
    )


def fetch(max_results: int = 5) -> list[Offer]:
    """Même limite que Inria : une requête = une phrase (AND), on essaie les
    mots-clés un par un plutôt que de tout concaténer."""
    from .. import config
    criteria = config.load_criteria()
    keywords = list(criteria.get("professions") or []) + list(criteria.get("stack") or [])

    offers: dict[str, Offer] = {}
    for keyword in keywords:
        if len(offers) >= max_results:
            break
        response = http.post(SEARCH_URL, data={
            "ctl00$CphMain$FormSearch$InputSearchBy": keyword,
            "Page": "0",
        })
        response.raise_for_status()
        for match in _CARD_RE.finditer(response.text):
            offer = _to_offer(match)
            offers.setdefault(offer.source_id, offer)
            if len(offers) >= max_results:
                break
    return list(offers.values())[:max_results]
