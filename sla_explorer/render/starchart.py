from __future__ import annotations

from rich.text import Text

from sla_world.domain.system import StarSystem
from sla_explorer.context import SimulationContext
from sla_explorer.palette import ColorAssignment, uncontrolled_color, civilization_color


def _line_cells(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    x0, y0 = start
    x1, y1 = end
    cells: list[tuple[int, int]] = []
    delta_x = abs(x1 - x0)
    delta_y = -abs(y1 - y0)
    step_x = 1 if x0 < x1 else -1
    step_y = 1 if y0 < y1 else -1
    error = delta_x + delta_y
    x, y = x0, y0
    while True:
        cells.append((x, y))
        if x == x1 and y == y1:
            break
        doubled_error = 2 * error
        if doubled_error >= delta_y:
            error += delta_y
            x += step_x
        if doubled_error <= delta_x:
            error += delta_x
            y += step_y
    return cells


class GalaxyMapRenderer:
    def __init__(self, context: SimulationContext) -> None:
        self._context = context
        self._colors = ColorAssignment(context.civilizations())

    def render(
        self, width: int, height: int, show_connections: bool = True
    ) -> tuple[Text, dict[tuple[int, int], StarSystem]]:
        width = max(width, 10)
        height = max(height, 5)
        systems = self._context.systems()
        if not systems:
            return Text("no systems generated"), {}

        min_x = min(system.position.x for system in systems)
        max_x = max(system.position.x for system in systems)
        min_y = min(system.position.y for system in systems)
        max_y = max(system.position.y for system in systems)
        span_x = max(max_x - min_x, 1e-6)
        span_y = max(max_y - min_y, 1e-6)

        def cell_for(system: StarSystem) -> tuple[int, int]:
            column = int((system.position.x - min_x) / span_x * (width - 1))
            row = int((system.position.y - min_y) / span_y * (height - 1))
            return column, row

        grid_char = [[" "] * width for _ in range(height)]
        grid_style = [[""] * width for _ in range(height)]
        cell_owner: dict[tuple[int, int], StarSystem] = {}

        if show_connections:
            self._draw_connections(cell_for, grid_char, grid_style)

        for system in systems:
            column, row = cell_for(system)
            symbol = "●" if system.is_controlled() else "○"
            style = self._colors.color_for(system.controlled_by)
            grid_char[row][column] = symbol
            grid_style[row][column] = style
            cell_owner[(column, row)] = system

        text = Text()
        for row in range(height):
            for column in range(width):
                text.append(grid_char[row][column], style=grid_style[row][column] or None)
            if row < height - 1:
                text.append("\n")
        return text, cell_owner

    def _draw_connections(self, cell_for, grid_char: list[list[str]], grid_style: list[list[str]]) -> None:
        galaxy = self._context.world.galaxy
        drawn: set[tuple[int, int]] = set()
        for connection in galaxy.connections.values():
            pair = (min(connection.a.value, connection.b.value), max(connection.a.value, connection.b.value))
            if pair in drawn:
                continue
            drawn.add(pair)
            system_a = galaxy.systems[connection.a]
            system_b = galaxy.systems[connection.b]
            for column, row in _line_cells(cell_for(system_a), cell_for(system_b)):
                if grid_char[row][column] == " ":
                    grid_char[row][column] = "·"
                    grid_style[row][column] = "grey35"


def galaxy_legend_text(context: SimulationContext) -> Text:
    text = Text()
    for index, civilization in enumerate(context.civilizations()):
        text.append("● ", style=civilization_color(index))
        text.append(f"{civilization.name}   ")
    text.append("○ ", style=uncontrolled_color())
    text.append("unclaimed")
    return text
