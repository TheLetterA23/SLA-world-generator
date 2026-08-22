from __future__ import annotations

from sla_world.domain.civilization import Civilization
from sla_world.domain.planet import PlanetType
from sla_world.infrastructure.ids import CivilizationId

_CIVILIZATION_COLORS = (
    "bright_red", "bright_green", "bright_yellow", "bright_blue",
    "bright_magenta", "bright_cyan", "red", "green", "yellow", "blue", "magenta", "cyan",
)

_UNCONTROLLED_COLOR = "grey58"

_PLANET_SYMBOLS = {
    PlanetType.ROCKY: "o",
    PlanetType.OCEAN: "≈",
    PlanetType.ICE: "*",
    PlanetType.GAS_GIANT: "◎",
    PlanetType.DESERT: "▵",
    PlanetType.VOLCANIC: "▲",
    PlanetType.BARREN: "·",
}


def civilization_color(index: int) -> str:
    return _CIVILIZATION_COLORS[index % len(_CIVILIZATION_COLORS)]


def uncontrolled_color() -> str:
    return _UNCONTROLLED_COLOR


def planet_symbol(planet_type: PlanetType) -> str:
    return _PLANET_SYMBOLS.get(planet_type, "o")


class ColorAssignment:
    def __init__(self, civilizations: list[Civilization]) -> None:
        self._colors = {
            civilization.id: civilization_color(index) for index, civilization in enumerate(civilizations)
        }

    def color_for(self, civilization_id: CivilizationId | None) -> str:
        if civilization_id is None:
            return uncontrolled_color()
        return self._colors.get(civilization_id, uncontrolled_color())
