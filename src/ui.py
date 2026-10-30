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
from .offer import Offer


# Champs disponibles pour input/table_columns.yaml -- voir le commentaire en tête
# de ce fichier yaml pour la liste à jour. Accès direct : le schéma Offer est
# déjà plat, plus besoin d'extraire quoi que ce soit d'une forme brute de site.
FIELD_GETTERS = {
    "name": lambda offer: offer.title,
    "company": lambda offer: offer.company,
    "city": lambda offer: offer.location,
    "contract_type": lambda offer: offer.contract_type,
    "source": lambda offer: offer.source,
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

    def __init__(self, jobs: list[Offer]) -> None:
        super().__init__()
        table_cfg = config.load_table_columns()
        self.columns = table_cfg["columns"]
        max_rows = int(table_cfg.get("max_rows", 100))
        self.jobs = jobs[:max_rows]
        self.max_rows = max_rows
        self.checked: set[int] = set()
        self.selected_jobs: list[Offer] = []

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


def run_selection_ui(jobs: list[Offer]) -> list[Offer]:
    app = JobTableApp(jobs)
    app.run()
    return app.selected_jobs


class SiteSelectionApp(App):
    """Liste à cocher pour choisir les sites à interroger (suffixe `sites` de run.ps1)."""

    BINDINGS = [
        Binding("space", "toggle", "Cocher/décocher"),
        Binding("enter", "submit", "Valider la sélection", priority=True),
        Binding("q", "quit_without", "Quitter sans rien faire"),
    ]
    CSS = """
    DataTable { height: 1fr; }
    """

    def __init__(self, sites: list[dict]) -> None:
        super().__init__()
        self.sites = sites
        self.checked: set[int] = set()
        self.selected_sites: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"Choisis les sites à interroger ({len(self.sites)} disponibles)"
        table = self.query_one(DataTable)
        table.add_columns(" ", "Site")
        for site in self.sites:
            table.add_row("[ ]", site.get("name") or site["slug"])
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
        self.selected_sites = [self.sites[i] for i in sorted(self.checked)]
        self.exit()

    def action_quit_without(self) -> None:
        self.selected_sites = []
        self.exit()


def run_site_selection_ui(sites: list[dict]) -> list[dict]:
    app = SiteSelectionApp(sites)
    app.run()
    return app.selected_sites
