from __future__ import annotations

from sla_world.simulation.context import StellarTickContext


class ExplorationHandler:
    def __init__(self, technology_growth: float = 0.001) -> None:
        self._technology_growth = technology_growth

    def execute(self, context: StellarTickContext) -> None:
        for civilization in context.universe.civilizations:
            civilization.development.technology += self._technology_growth
