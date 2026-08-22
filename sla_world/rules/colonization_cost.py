from __future__ import annotations

from typing import Protocol

from sla_world.domain.civilization import Civilization
from sla_world.domain.planet import Planet
from sla_world.domain.resources import ResourceInventory, ResourceType


class ColonizationCostCalculator(Protocol):
    def cost_for(self, civilization: Civilization, planet: Planet) -> ResourceInventory: ...


class FlatColonizationCost:
    def __init__(self, cost: ResourceInventory | None = None) -> None:
        self._cost = cost or ResourceInventory(
            {
                ResourceType.IRON: 50.0,
                ResourceType.ENERGY_CRYSTALS: 10.0,
            }
        )

    def cost_for(self, civilization: Civilization, planet: Planet) -> ResourceInventory:
        return self._cost


class HabitabilityScaledCost:
    def __init__(self, base_cost: ResourceInventory | None = None, difficulty_multiplier: float = 2.0) -> None:
        self._base_cost = base_cost or ResourceInventory(
            {
                ResourceType.IRON: 50.0,
                ResourceType.ENERGY_CRYSTALS: 10.0,
            }
        )
        self._difficulty_multiplier = difficulty_multiplier

    def cost_for(self, civilization: Civilization, planet: Planet) -> ResourceInventory:
        habitability = planet.habitability.base_score
        scale = 1.0 + self._difficulty_multiplier * (1.0 - habitability)
        return ResourceInventory({resource: quantity * scale for resource, quantity in self._base_cost.amounts.items()})
