from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static

from sla_world.domain.system import StarSystem
from sla_explorer.context import SimulationContext
from sla_explorer.tui.support import context_of
from sla_explorer.render.starchart import GalaxyMapRenderer, galaxy_legend_text
from sla_explorer.tui.widgets.starchart_widget import GalaxyMapWidget
from sla_explorer.tui.screens.systems import SystemDetailScreen


class GalaxyMapScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def compose(self) -> ComposeResult:
        context: SimulationContext = context_of(self)
        renderer = GalaxyMapRenderer(context)
        self._chart = GalaxyMapWidget(renderer, self._open_system, id="chart")
        yield Header()
        yield self._chart
        yield Static(galaxy_legend_text(context), id="legend")
        yield Static("Click a system to open its chart.", id="hint")
        yield Footer()

    def on_mount(self) -> None:
        self._chart.redraw()

    def on_resize(self, event: events.Resize) -> None:
        self._chart.redraw()

    def _open_system(self, system: StarSystem) -> None:
        self.app.push_screen(SystemDetailScreen(system))
