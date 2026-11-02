"""Langue d'une offre (fr / en) par comptage de mots-outils : volontairement
frugal, sans modèle ni dépendance. Sert à choisir le CV et la LM (français ou
anglais) à générer pour l'offre."""
from __future__ import annotations

import re

from .offer import Offer

# Mots-outils fréquents et non ambigus : on écarte ceux qui existent dans les deux
# langues (a, on, or, as, an, pour/four...) pour ne pas biaiser le comptage.
_FR = set("le la les des du de un une et est pour avec dans sur vous nous notre votre ce cette ces au aux "
          "en qui que par pas plus où nos vos sont être avoir à chez ainsi mais vos leur leurs aussi".split())
_EN = set("the and of to for with you we our your in is are will be at by this that from have has their "
          "they who what which about into also not but all can your us".split())
_WORD = re.compile(r"[a-zàâçéèêëîïôûùüÿœ']+")

DEFAULT = "fr"


def detect(offer: Offer) -> str:
    """'en' si l'offre contient plus de mots-outils anglais que français, sinon 'fr' (égalité / texte vide -> 'fr')."""
    words = _WORD.findall(f"{offer.title} {offer.description[:3000]}".lower())
    fr = sum(w in _FR for w in words)
    en = sum(w in _EN for w in words)
    return "en" if en > fr else DEFAULT


def detect_text(text: str) -> str | None:
    """Langue d'un texte court (ex. les questions d'un formulaire) ; None si indécidable (aucun mot-outil, égalité)."""
    words = _WORD.findall(text.lower())
    fr = sum(w in _FR for w in words)
    en = sum(w in _EN for w in words)
    return None if fr == en else ("en" if en > fr else "fr")
