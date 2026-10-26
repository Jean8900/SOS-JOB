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


def load_criteria() -> dict:
    return _load("criteria.yaml")


def load_companies() -> dict:
    return _load("companies.yaml")


def load_table_columns() -> dict:
    return _load("table_columns.yaml")


def load_cv_template() -> dict:
    return _load("cv_template.yaml")
