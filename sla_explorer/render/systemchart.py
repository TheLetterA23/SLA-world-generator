from __future__ import annotations

from rich.table import Table
from rich.text import Text

from sla_world.domain.system import StarSystem
from sla_explorer.context import SimulationContext
from sla_explorer.palette import ColorAssignment, uncontrolled_color, planet_symbol


class SystemChartRenderer:
    def __init__(self, context: SimulationContext) -> None:
        self._context = context
        self._colors = ColorAssignment(context.civilizations())

    def render_diagram(self, system: StarSystem, spacing: int = 6) -> Text:
        planets = system.planets()
        star_class = system.stars[0].spectral_class if system.stars else "?"

        header = Text()
        header.append(f"{system.name}", style="bold")
        header.append(f"  ({star_class}-class star, {len(planets)} planets)\n\n", style="dim")

        orbit_line = Text("★", style="bold yellow")
        label_line = Text(" ")
        for index, planet in enumerate(planets, start=1):
            orbit_line.append("─" * spacing, style="grey35")
            color = self._colors.color_for(planet.owner)
            orbit_line.append(planet_symbol(planet.planet_type), style=color)
            label_line.append(" " * spacing)
            label_line.append(str(index).rjust(1), style="dim")
        if system.asteroid_belts():
            orbit_line.append("─" * spacing, style="grey35")
            orbit_line.append("∴", style="grey58")

        diagram = Text()
        diagram.append(header)
        diagram.append(orbit_line)
        diagram.append("\n")
        diagram.append(label_line)
        return diagram

    def planet_table(self, system: StarSystem) -> Table:
        table = Table(title=f"Planets in {system.name}")
        table.add_column("#", justify="right")
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Habitable")
        table.add_column("Owner")
        table.add_column("Moons", justify="right")
        for index, planet in enumerate(system.planets(), start=1):
            owner_name = "—"
            if planet.owner is not None:
                owner_name = self._context.world.civilization(planet.owner).name
            table.add_row(
                str(index),
                planet.name,
                planet.planet_type.name.replace("_", " ").title(),
                "yes" if planet.is_habitable() else "no",
                owner_name,
                str(len(planet.moon_ids)),
            )
        return table

    def system_summary_table(self, system: StarSystem) -> Table:
        traffic = self._context.world.details.traffic_for(system)
        owner_name = "unclaimed"
        if system.controlled_by is not None:
            owner_name = self._context.world.civilization(system.controlled_by).name
        table = Table(title="System Summary", show_header=False, box=None)
        table.add_row("Position", f"({system.position.x:.1f}, {system.position.y:.1f}, {system.position.z:.1f})")
        table.add_row("Stars", str(len(system.stars)))
        table.add_row("Planets", str(len(system.planets())))
        table.add_row("Moons", str(len(system.moons())))
        table.add_row("Asteroid belts", str(len(system.asteroid_belts())))
        table.add_row("Connections", str(len(system.connection_ids)))
        table.add_row("Controlled by", owner_name)
        table.add_row("Resource value", f"{system.resource_summary.total_value():.1f}")
        table.add_row("Est. traffic", f"{traffic.estimated_ships} ships, {traffic.congestion:.0%} congestion")
        return table
