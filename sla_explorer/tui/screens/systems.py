from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Input, Static

from sla_world.domain.system import StarSystem
from sla_world.infrastructure.ids import SystemId
from sla_explorer.context import SimulationContext
from sla_explorer.tui.support import context_of, row_key_int
from sla_explorer.render.systemchart import SystemChartRenderer


class SystemListScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="filter by name…", id="filter")
        table: DataTable = DataTable(id="system-table")
        table.cursor_type = "row"
        table.add_columns("ID", "Name", "Star", "Planets", "Controlled by")
        yield table
        yield Footer()

    def on_mount(self) -> None:
        self._populate("")
        self.query_one("#system-table", DataTable).focus()

    def _populate(self, query: str) -> None:
        context: SimulationContext = context_of(self)
        table = self.query_one("#system-table", DataTable)
        table.clear()
        lowered = query.lower()
        for system in context.systems():
            if lowered and lowered not in system.name.lower():
                continue
            star_class = system.stars[0].spectral_class if system.stars else "?"
            owner = context.world.civilization(system.controlled_by).name if system.controlled_by else "—"
            table.add_row(
                f"#{system.id.value}",
                system.name,
                star_class,
                str(len(system.planets())),
                owner,
                key=str(system.id.value),
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        self._populate(event.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        context: SimulationContext = context_of(self)
        system = context.world.find_system(SystemId(row_key_int(event.row_key)))
        self.app.push_screen(SystemDetailScreen(system))


class SystemDetailScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(self, system: StarSystem) -> None:
        super().__init__()
        self.system = system

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="diagram")
        yield DataTable(id="planet-table")
        yield Static(id="summary")
        yield Footer()

    def on_mount(self) -> None:
        context: SimulationContext = context_of(self)
        renderer = SystemChartRenderer(context)

        self.query_one("#diagram", Static).update(renderer.render_diagram(self.system))

        planet_table = self.query_one("#planet-table", DataTable)
        planet_table.add_columns("#", "Name", "Type", "Habitable", "Owner", "Moons")
        for index, planet in enumerate(self.system.planets(), start=1):
            owner_name = context.world.civilization(planet.owner).name if planet.owner else "—"
            planet_table.add_row(
                str(index),
                planet.name,
                planet.planet_type.name.replace("_", " ").title(),
                "yes" if planet.is_habitable() else "no",
                owner_name,
                str(len(planet.moon_ids)),
            )

        self.query_one("#summary", Static).update(renderer.system_summary_table(self.system))
