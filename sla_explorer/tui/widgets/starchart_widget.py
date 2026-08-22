from __future__ import annotations

from typing import Callable

from textual import events
from textual.widgets import Static

from sla_world.domain.system import StarSystem
from sla_explorer.render.starchart import GalaxyMapRenderer


class GalaxyMapWidget(Static):
    def __init__(self, renderer: GalaxyMapRenderer, on_select: Callable[[StarSystem], None], **kwargs) -> None:
        super().__init__(**kwargs)
        self._renderer = renderer
        self._on_select = on_select
        self._cells: dict[tuple[int, int], StarSystem] = {}

    def redraw(self, show_connections: bool = True) -> None:
        width = max(self.size.width, 20)
        height = max(self.size.height, 10)
        text, cells = self._renderer.render(width=width, height=height, show_connections=show_connections)
        self._cells = cells
        self.update(text)

    def on_click(self, event: events.Click) -> None:
        system = self._cells.get((event.x, event.y))
        if system is not None:
            self._on_select(system)
