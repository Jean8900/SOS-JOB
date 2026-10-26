"""TUI terminal (textual) : tableau des offres avec cases à cocher.

↑/↓ naviguer · espace cocher/décocher · entrée valider · q quitter sans rien faire.

Les colonnes affichées se règlent dans input/table_columns.yaml, pas ici.
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Footer, Header

from . import config


def _job_city(job: dict) -> str:
    offices = job.get("offices") or ([job["office"]] if job.get("office") else [])
    for office in offices:
        if office and office.get("city"):
            return office["city"]
    if job.get("remote") in ("full", "partial"):
        return "Remote"
    return "?"


def _job_company(job: dict) -> str:
    org = job.get("organization") or {}
    return org.get("name") or job.get("_source_company_slug") or "?"


# Champs disponibles pour input/table_columns.yaml -- voir le commentaire en tête
# de ce fichier yaml pour la liste à jour.
FIELD_GETTERS = {
    "name": lambda job: job.get("name") or "",
    "company": _job_company,
    "city": _job_city,
    "contract_type": lambda job: str(job.get("contract_type") or ""),
    "remote": lambda job: str(job.get("remote") or ""),
}


class JobTableApp(App):
    BINDINGS = [
        Binding("space", "toggle", "Cocher/décocher"),
        Binding("enter", "submit", "Valider la sélection", priority=True),
        Binding("q", "quit_without", "Quitter sans rien faire"),
    ]
    CSS = """
    DataTable { height: 1fr; }
    """

    def __init__(self, jobs: list[dict]) -> None:
        super().__init__()
        table_cfg = config.load_table_columns()
        self.columns = table_cfg["columns"]
        max_rows = int(table_cfg.get("max_rows", 100))
        self.jobs = jobs[:max_rows]
        self.max_rows = max_rows
        self.checked: set[int] = set()
        self.selected_jobs: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"Offres de la semaine ({len(self.jobs)}/{self.max_rows})"
        table = self.query_one(DataTable)
        table.add_columns(" ", *(col["label"] for col in self.columns))
        for job in self.jobs:
            cells = []
            for col in self.columns:
                getter = FIELD_GETTERS.get(col["field"])
                value = getter(job) if getter else f"?champ inconnu: {col['field']}?"
                cells.append(value[: col.get("width", 30)])
            table.add_row("[ ]", *cells)
        table.focus()

    def action_toggle(self) -> None:
        table = self.query_one(DataTable)
        row_index = table.cursor_row
        if row_index is None:
            return
        if row_index in self.checked:
            self.checked.discard(row_index)
            mark = "[ ]"
        else:
            self.checked.add(row_index)
            mark = "[x]"
        table.update_cell_at(Coordinate(row_index, 0), mark)

    def action_submit(self) -> None:
        self.selected_jobs = [self.jobs[i] for i in sorted(self.checked)]
        self.exit()

    def action_quit_without(self) -> None:
        self.selected_jobs = []
        self.exit()


def run_selection_ui(jobs: list[dict]) -> list[dict]:
    app = JobTableApp(jobs)
    app.run()
    return app.selected_jobs
