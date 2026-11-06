"""Point d'accès unique aux fichiers éditables par l'utilisateur, tous dans input/.

Rien dans src/ ne doit contenir de valeur "à toi" (critère, entreprise, colonne,
texte du CV...) -- tout ça vit dans input/, voir input/README.md.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = REPO_ROOT / "input"


def _load(filename: str) -> dict:
    with (INPUT_DIR / filename).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


_criteria_override: dict = {}


def set_criteria_override(values: dict) -> None:
    """Critères du formulaire de go.py : priment sur criteria.yaml le temps du processus, sans réécrire le fichier."""
    _criteria_override.clear()
    _criteria_override.update(values)


def load_criteria() -> dict:
    return {**_load("criteria.yaml"), **_criteria_override}


def load_companies() -> dict:
    return _load("companies.yaml")


def load_table_columns() -> dict:
    return _load("table_columns.yaml")


def load_cv_template() -> dict:
    return _load("cv_template.yaml")


def load_ats_companies() -> dict:
    return _load("ats_companies.yaml")


def load_copilot() -> dict:
    return _load("copilot.yaml")


def load_sites() -> dict:
    return _load("sites.yaml")


def load_form_profile() -> dict:
    """Infos perso réservées aux formulaires (adresse...) : input/form_profile.yaml, absent = aucune info."""
    try:
        return _load("form_profile.yaml") or {}
    except FileNotFoundError:
        return {}
