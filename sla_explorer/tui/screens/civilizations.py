from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, TabbedContent, TabPane, Static

from sla_world.domain.civilization import Civilization
from sla_world.infrastructure.ids import CivilizationId
from sla_explorer.context import SimulationContext
from sla_explorer.tui.support import context_of, row_key_int
from sla_explorer.render.civilizations import civilization_rows, civilization_planet_rows, format_event


class CivilizationListScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        table: DataTable = DataTable(id="civ-table")
        table.cursor_type = "row"
        table.add_columns("ID", "Name", "Systems", "Planets", "Tech", "Spreading Power")
        yield table
        yield Footer()

    def on_mount(self) -> None:
        context: SimulationContext = context_of(self)
        table = self.query_one("#civ-table", DataTable)
        for row in civilization_rows(context):
            table.add_row(
                f"#{row.civilization.id.value}",
                row.civilization.name,
                str(row.system_count),
                str(row.planet_count),
                f"{row.technology:.2f}",
                f"{row.spreading_power:.3f}",
                key=str(row.civilization.id.value),
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        context: SimulationContext = context_of(self)
        civilization = context.world.civilization(CivilizationId(row_key_int(event.row_key)))
        self.app.push_screen(CivilizationDetailScreen(civilization))


class CivilizationDetailScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(self, civilization: Civilization) -> None:
        super().__init__()
        self.civilization = civilization

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Overview", id="overview"):
                yield Static(id="overview-body")
            with TabPane("Planets", id="planets"):
                yield DataTable(id="planet-table")
            with TabPane("Systems", id="systems"):
                yield DataTable(id="system-table")
            with TabPane("History", id="history"):
                yield DataTable(id="history-table")
        yield Footer()

    def on_mount(self) -> None:
        context: SimulationContext = context_of(self)
        civilization = self.civilization

        self.query_one("#overview-body", Static).update(self._overview_text(context, civilization))

        planet_table = self.query_one("#planet-table", DataTable)
        planet_table.add_columns("Planet", "System", "Type", "Habitability", "Development")
        for row in civilization_planet_rows(context, civilization):
            planet_table.add_row(
                row.planet.name,
                row.system_name,
                row.planet.planet_type.name.replace("_", " ").title(),
                f"{row.planet.habitability.base_score:.2f}",
                f"{row.development_level:.2f}",
            )

        system_table = self.query_one("#system-table", DataTable)
        system_table.add_columns("System", "Owned / Total planets", "Position")
        for system in context.world.controlled_systems(civilization):
            owned = sum(1 for planet in system.planets() if planet.owner == civilization.id)
            system_table.add_row(
                system.name,
                f"{owned}/{len(system.planets())}",
                f"({system.position.x:.0f}, {system.position.y:.0f}, {system.position.z:.0f})",
            )

        history_table = self.query_one("#history-table", DataTable)
        history_table.add_columns("Time", "Event", "Details")
        for event in sorted(civilization.history.events, key=lambda event: event.time):
            history_table.add_row(str(event.time), event.kind, format_event(context, event))

    def _overview_text(self, context: SimulationContext, civilization: Civilization) -> str:
        origin = context.world.origin_world(civilization)
        return (
            f"Origin world: {origin.name}  (habitability {origin.habitability.base_score:.2f})\n"
            f"Technology: {civilization.development.technology:.2f}\n"
            f"Industrialization: {civilization.development.industrialization:.2f}\n"
            f"Infrastructure: {civilization.development.infrastructure:.2f}\n"
            f"Population index: {civilization.development.population:.2f}\n"
            f"Spreading power: {context.world.spreading_power(civilization):.3f}\n"
            f"Active trade routes: {len(civilization.trade.active_routes())}"
        )
