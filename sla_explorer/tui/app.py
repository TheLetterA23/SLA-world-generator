from __future__ import annotations

from pathlib import Path

from textual.app import App
from textual.binding import Binding

from sla_explorer.context import SimulationContext
from sla_explorer.tui.screens.home import HomeScreen


class SLAExplorerApp(App):
    CSS_PATH = Path(__file__).with_name("app.tcss")
    BINDINGS = [Binding("q", "quit", "Quit")]
    TITLE = "SLA Universe Explorer"

    def __init__(self, context: SimulationContext) -> None:
        super().__init__()
        self.context = context

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())
