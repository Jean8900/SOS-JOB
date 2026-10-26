"""Déplace toutes les LM générées (tex + pdf) vers l'archive.

Si une LM du même nom existe déjà dans l'archive, elle est écrasée.

Usage : python archive_lm.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src import lm_builder  # noqa: E402


def archive_all() -> int:
    moved = 0
    for src_dir, dst_dir in (
        (lm_builder.OUTPUT_TEX_DIR, lm_builder.ARCHIVE_TEX_DIR),
        (lm_builder.OUTPUT_PDF_DIR, lm_builder.ARCHIVE_PDF_DIR),
    ):
        dst_dir.mkdir(parents=True, exist_ok=True)
        if not src_dir.exists():
            continue
        for f in src_dir.iterdir():
            if not f.is_file() or f.name == ".gitkeep":
                continue
            dst = dst_dir / f.name
            if dst.exists():
                dst.unlink()
            shutil.move(str(f), str(dst))
            moved += 1
    return moved


def main() -> None:
    moved = archive_all()
    print(f"{moved} fichier(s) archivé(s) -> output/LM/archive/")


if __name__ == "__main__":
    main()
