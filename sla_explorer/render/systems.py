from __future__ import annotations

from rich.table import Table

from sla_explorer.context import SimulationContext


def system_table(context: SimulationContext, name_filter: str = "") -> Table:
    table = Table(title="Systems")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Star")
    table.add_column("Planets", justify="right")
    table.add_column("Controlled by")
    lowered = name_filter.lower()
    for system in context.systems():
        if lowered and lowered not in system.name.lower():
            continue
        star_class = system.stars[0].spectral_class if system.stars else "?"
        owner = context.world.civilization(system.controlled_by).name if system.controlled_by else "—"
        table.add_row(f"#{system.id.value}", system.name, star_class, str(len(system.planets())), owner)
    return table
