"""Génère output/suivi.xlsx (une ligne par candidature) et l'ouvre.

Usage : python suivi.py
Tu peux écrire dans la colonne Notes et ajouter tes propres lignes : elles sont
conservées à chaque régénération.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import suivi  # noqa: E402


def main() -> None:
    path = suivi.build()
    print(f"{path.name} mis à jour : {path}")
    try:
        os.startfile(path)
    except OSError:
        print("Aucune application n'est associée aux fichiers .xlsx (Excel / LibreOffice non installé ?).")
        print("Ouvre-le avec Excel ou LibreOffice, ou importe-le dans Google Sheets (Fichier > Importer).")
        subprocess.Popen(["explorer.exe", f"/select,{path}"])


if __name__ == "__main__":
    main()
