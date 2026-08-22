from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, OptionList, Static
from textual.widgets.option_list import Option

from sla_explorer.context import SimulationContext
from sla_explorer.tui.support import context_of
from sla_explorer.tui.screens.civilizations import CivilizationListScreen
from sla_explorer.tui.screens.systems import SystemListScreen
from sla_explorer.tui.screens.galaxy import GalaxyMapScreen


class HomeScreen(Screen):
    BINDINGS = [("escape", "app.quit", "Quit"), ("q", "app.quit", "Quit")]

    def compose(self) -> ComposeResult:
        context: SimulationContext = context_of(self)
        yield Header()
        yield Static(self._summary_text(context), id="summary")
        yield OptionList(
            Option("Civilizations", id="civilizations"),
            Option("Galaxy Map", id="galaxy"),
            Option("Systems", id="systems"),
            id="menu",
        )
        yield Footer()

    def _summary_text(self, context: SimulationContext) -> str:
        settings = context.settings
        return (
            f"Seed {settings.seed}   |   {len(context.systems())} systems   |   "
            f"{len(context.civilizations())} civilizations   |   simulated time {context.simulated_time}"
        )

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option.id
        if option_id == "civilizations":
            self.app.push_screen(CivilizationListScreen())
        elif option_id == "galaxy":
            self.app.push_screen(GalaxyMapScreen())
        elif option_id == "systems":
            self.app.push_screen(SystemListScreen())
