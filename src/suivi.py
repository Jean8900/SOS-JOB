"""Suivi des candidatures : output/suivi.xlsx, une ligne par offre candidatée
(Date, Entreprise, Poste, Site, Lien, Mise à jour, Notes), régénéré depuis
output/applications.json.

Notes = historique, dernier état en premier : "texte_update // texte_legacy".
Tu tapes une nouvelle info dans « Mise à jour » ; à la prochaine génération elle
passe devant Notes et la cellule se vide.

Ce que tu écris à la main n'est jamais perdu : les lignes que tu ajoutes
toi-même (candidatures hors outil) restent en bas, et une offre qui n'est plus
« candidatée » mais qui a une note reste aussi. Les colonnes sont retrouvées par
leur titre, l'offre par un identifiant caché (dernière colonne)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

from . import applications

REPO_ROOT = Path(__file__).resolve().parent.parent
XLSX_PATH = REPO_ROOT / "output" / "suivi.xlsx"

HEADERS = ("Date", "Entreprise", "Poste", "Site", "Lien", "Mise à jour", "Notes", "id")
WIDTHS = (12, 28, 48, 24, 10, 30, 70, 10)
SEPARATOR = " // "
_LINK, _ID = HEADERS.index("Lien"), HEADERS.index("id")
_UPDATE_FILL = PatternFill("solid", fgColor="FFF4CC")  # colonne où tu écris


def _local_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%d/%m/%Y")
    except ValueError:
        return ""


def _put(sheet, row: int, col: int, value) -> None:
    """Toujours du texte : un titre d'offre commençant par '=' ne doit jamais devenir une formule Excel."""
    cell = sheet.cell(row=row, column=col)
    cell.value = "" if value is None else str(value)
    cell.data_type = "s"


def merge_note(update: str, legacy: str) -> str:
    """'update // legacy' : le dernier état d'abord, l'historique derrière."""
    update, legacy = (update or "").strip(), (legacy or "").strip()
    return f"{update}{SEPARATOR}{legacy}" if update and legacy else update or legacy


def _read_existing(path: Path, applied_ids: set[str]) -> tuple[dict[str, str], list[list]]:
    """(notes fusionnées par id, lignes à reporter : lignes manuelles + offres sorties de la liste mais annotées)."""
    notes: dict[str, str] = {}
    kept: list[list] = []
    if not path.exists():
        return notes, kept
    sheet = load_workbook(path).active
    col = {cell.value: i for i, cell in enumerate(sheet[1]) if cell.value}  # retrouvé par titre de colonne
    for row in sheet.iter_rows(min_row=2):
        def get(name: str):
            i = col.get(name)
            return row[i].value if i is not None and i < len(row) else None

        row_id, note = get("id"), merge_note(get("Mise à jour"), get("Notes"))
        values = [get(h) for h in HEADERS[:_ID]]
        values[HEADERS.index("Mise à jour")], values[HEADERS.index("Notes")] = "", note
        if row_id in applied_ids:
            if note:
                notes[row_id] = note
        elif row_id:
            if note:  # offre plus candidatée mais annotée : on garde la ligne
                kept.append(values + [row_id])
        elif any(v not in (None, "") for v in values):  # ligne ajoutée à la main
            kept.append(values + [""])
    return notes, kept


def build(path: Path = XLSX_PATH) -> Path:
    rows = applications.applied()
    notes, kept = _read_existing(path, {key for key, _, _ in rows})

    wb = Workbook()
    sheet = wb.active
    sheet.title = "Candidatures"
    for col, header in enumerate(HEADERS, start=1):
        _put(sheet, 1, col, header)
        sheet.cell(row=1, column=col).font = Font(bold=True)
    sheet.cell(row=1, column=HEADERS.index("Mise à jour") + 1).fill = _UPDATE_FILL

    line = 2
    for key, offer, applied_at in rows:
        values = [_local_date(applied_at), offer.company, offer.title.strip(), offer.source, "ouvrir", "",
                  notes.get(key, ""), key]
        for col, value in enumerate(values, start=1):
            _put(sheet, line, col, value)
        if offer.url.startswith(("http://", "https://")):  # jamais de file:, javascript:, etc.
            link = sheet.cell(row=line, column=_LINK + 1)
            link.hyperlink = offer.url
            link.font = Font(color="0563C1", underline="single")
        line += 1
    for values in kept:
        for col, value in enumerate(values, start=1):
            _put(sheet, line, col, value)
        line += 1

    for i, width in enumerate(WIDTHS, start=1):
        sheet.column_dimensions[sheet.cell(row=1, column=i).column_letter].width = width
    sheet.column_dimensions[sheet.cell(row=1, column=_ID + 1).column_letter].hidden = True
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:G{max(line - 1, 1)}"

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        wb.save(path)
    except PermissionError:
        raise SystemExit(f"{path.name} est ouvert dans Excel : ferme-le puis relance (tes notes sont conservées).")
    return path
