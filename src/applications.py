"""Suivi des candidatures : un fichier d'état (output/applications.json) avec
un statut par offre (pending / applied / skipped). Alimenté par run.py après
la génération des CV/LM, consommé par apply.py (copilot)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import cv_builder, lm_builder
from .offer import Offer

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "output" / "applications.json"

PENDING, APPLIED, SKIPPED = "pending", "applied", "skipped"


def offer_key(offer: Offer) -> str:
    return f"{offer.source}:{offer.source_id}"


def _load() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def locate_pdfs(offer: Offer) -> tuple[Path | None, Path | None]:
    """(CV, LM) PDF générés pour cette offre. La LM peut avoir été déplacée dans l'archive."""
    cv = cv_builder.pdf_dir_for_source(offer.source) / f"{cv_builder.basename_for_offer(offer)}.pdf"
    lm_name = f"{lm_builder.basename_for_job(offer)}.pdf"
    lm = next((p for p in (lm_builder.pdf_dir_for_source(offer.source) / lm_name,
                           lm_builder.archive_pdf_dir_for_source(offer.source) / lm_name) if p.exists()), None)
    return (cv if cv.exists() else None), lm


def register(offers: list[Offer]) -> int:
    """Ajoute (sans toucher au statut des offres déjà connues) les offres dont CV et LM existent. Retourne le nb d'ajouts."""
    state = _load()
    added = 0
    for offer in offers:
        key = offer_key(offer)
        if key in state:
            continue
        cv, lm = locate_pdfs(offer)
        if cv is None or lm is None:
            continue
        state[key] = {"status": PENDING, "offer": offer.model_dump(), "added_at": datetime.now(timezone.utc).isoformat()}
        added += 1
    _save(state)
    return added


def pending() -> list[tuple[str, Offer]]:
    return [(k, Offer(**v["offer"])) for k, v in _load().items() if v["status"] == PENDING]


def statuses() -> dict[str, str]:
    return {k: v["status"] for k, v in _load().items()}


def status_of(key: str) -> str:
    return _load().get(key, {}).get("status", "")


def set_status(key: str, status: str) -> None:
    state = _load()
    state[key]["status"] = status
    state[key]["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save(state)
