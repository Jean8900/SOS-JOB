"""Connecteur Choisir le service public (choisirleservicepublic.gouv.fr) --
job 1 (analyse) :

Site WordPress ; endpoint custom `/wp-json/api/offer-list` (POST) trouvé via
l'index `/wp-json/` -- mais UNIQUEMENT sur le domaine SANS `www.` (la variante
`www.` renvoie 404 sur cette route, piège observé en test). Le paramètre de
mot-clé de ce endpoint (`keyword` côté formulaire JS) n'a pas d'effet mesuré
en test (le total retourné ne change pas) -- limite connue, documentée ici
plutôt que masquée. On récupère donc les offres les plus récentes sans filtre
serveur, et c'est `src/matcher.py` qui fait tout le travail de filtrage côté
client, comme pour les autres connecteurs.

Pas de description/contract_type dans cette réponse (champs absents de
l'API) -- limite connue, acceptable pour l'instant (voir TODO).
"""
from __future__ import annotations

import re

from ..offer import Offer
from . import http

SOURCE = "choisir_service_public"
API_URL = "https://choisirleservicepublic.gouv.fr/wp-json/api/offer-list"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _to_offer(item: dict) -> Offer:
    reference = item.get("reference") or item["url"].rstrip("/").rsplit("-", 1)[-1]
    return Offer(
        source=SOURCE,
        source_id=reference,
        url=item["url"],
        url_canonique=item["url"],
        title=item.get("title") or "",
        company=item.get("employeur") or "",
        location=_strip_html(item.get("localisation") or ""),
        contract_type="",
        description=item.get("domain") or "",
        posted_at=item.get("publication_date"),
    )


def fetch(max_results: int = 5) -> list[Offer]:
    response = http.post(API_URL, json={}, headers={"Content-Type": "application/json"})
    response.raise_for_status()
    data = response.json()
    items = (data.get("items") or [])[:max_results]
    return [_to_offer(item) for item in items]
