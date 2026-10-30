"""Schéma unique pour toute offre, quelle que soit sa source.

Chaque connecteur (src/connectors/*.py) convertit les données brutes de son
site en une liste d'Offer -- le reste du pipeline (matcher, ui, cv_builder,
lm_builder) ne connaît plus que ce schéma, jamais la forme brute d'un site.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Offer(BaseModel):
    source: str  # slug du site, ex: "welcome_to_the_jungle", "free_work"
    source_id: str  # identifiant stable côté source (utilisé pour le nommage de fichiers)
    url: str
    url_canonique: str
    title: str
    company: str
    location: str = ""
    contract_type: str = ""
    description: str = ""  # texte brut (pas de HTML) -- nettoyé par le connecteur
    posted_at: str | None = None
    fetched_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
