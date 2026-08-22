from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from sla_world.domain.civilization import Civilization, SimulationEvent
from sla_world.domain.planet import Planet
from sla_world.infrastructure.ids import StellarObjectId, SystemId
from sla_explorer.context import SimulationContext


@dataclass(frozen=True)
class CivilizationRow:
    civilization: Civilization
    system_count: int
    planet_count: int
    spreading_power: float
    technology: float


def civilization_rows(context: SimulationContext) -> list[CivilizationRow]:
    return [
        CivilizationRow(
            civilization=civilization,
            system_count=len(civilization.controlled_system_ids),
            planet_count=len(civilization.controlled_planet_ids),
            spreading_power=context.world.spreading_power(civilization),
            technology=civilization.development.technology,
        )
        for civilization in context.civilizations()
    ]


def civilization_table(context: SimulationContext) -> Table:
    table = Table(title="Civilizations")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Systems", justify="right")
    table.add_column("Planets", justify="right")
    table.add_column("Tech", justify="right")
    table.add_column("Spreading Power", justify="right")
    for row in civilization_rows(context):
        table.add_row(
            f"#{row.civilization.id.value}",
            row.civilization.name,
            str(row.system_count),
            str(row.planet_count),
            f"{row.technology:.2f}",
            f"{row.spreading_power:.3f}",
        )
    return table


@dataclass(frozen=True)
class PlanetRow:
    planet: Planet
    system_name: str
    development_level: float


def civilization_planet_rows(context: SimulationContext, civilization: Civilization) -> list[PlanetRow]:
    rows = []
    for planet in context.world.controlled_planets(civilization):
        system_name = "?"
        if planet.parent_system_id is not None:
            system_name = context.world.find_system(planet.parent_system_id).name
        rows.append(PlanetRow(planet=planet, system_name=system_name, development_level=planet.development_level))
    rows.sort(key=lambda row: row.planet.name)
    return rows


def civilization_planet_table(context: SimulationContext, civilization: Civilization) -> Table:
    table = Table(title=f"Planets controlled by {civilization.name}")
    table.add_column("Planet")
    table.add_column("System")
    table.add_column("Type")
    table.add_column("Habitability", justify="right")
    table.add_column("Development", justify="right")
    for row in civilization_planet_rows(context, civilization):
        table.add_row(
            row.planet.name,
            row.system_name,
            row.planet.planet_type.name.replace("_", " ").title(),
            f"{row.planet.habitability.base_score:.2f}",
            f"{row.development_level:.2f}",
        )
    return table


def civilization_systems_table(context: SimulationContext, civilization: Civilization) -> Table:
    table = Table(title=f"Systems controlled by {civilization.name}")
    table.add_column("System")
    table.add_column("Owned / Total planets")
    table.add_column("Position")
    for system in context.world.controlled_systems(civilization):
        owned = sum(1 for planet in system.planets() if planet.owner == civilization.id)
        table.add_row(
            system.name,
            f"{owned}/{len(system.planets())}",
            f"({system.position.x:.0f}, {system.position.y:.0f}, {system.position.z:.0f})",
        )
    return table


def civilization_overview(context: SimulationContext, civilization: Civilization) -> Panel:
    origin = context.world.origin_world(civilization)
    body = Text()
    body.append(f"Origin world: {origin.name} (habitability {origin.habitability.base_score:.2f})\n")
    body.append(f"Technology: {civilization.development.technology:.2f}\n")
    body.append(f"Industrialization: {civilization.development.industrialization:.2f}\n")
    body.append(f"Infrastructure: {civilization.development.infrastructure:.2f}\n")
    body.append(f"Population index: {civilization.development.population:.2f}\n")
    body.append(f"Spreading power: {context.world.spreading_power(civilization):.3f}\n")
    body.append(f"Active trade routes: {len(civilization.trade.active_routes())}")
    return Panel(body, title=f"{civilization.name}  (#{civilization.id.value})")


def format_event(context: SimulationContext, event: SimulationEvent) -> str:
    if event.kind == "PlanetColonized":
        planet_id = cast(int, event.data["planet_id"])
        system_id = cast(int, event.data["system_id"])
        planet = context.world.find_planet(StellarObjectId(planet_id))
        system = context.world.find_system(SystemId(system_id))
        return f"colonized {planet.name} in system {system.name}"
    if event.kind == "SystemClaimed":
        system_id = cast(int, event.data["system_id"])
        system = context.world.find_system(SystemId(system_id))
        return f"claimed system {system.name}"
    return event.kind


def civilization_history_table(context: SimulationContext, civilization: Civilization) -> Table:
    table = Table(title=f"History of {civilization.name}")
    table.add_column("Time", justify="right")
    table.add_column("Event")
    table.add_column("Details")
    for event in sorted(civilization.history.events, key=lambda event: event.time):
        table.add_row(str(event.time), event.kind, format_event(context, event))
    return table
