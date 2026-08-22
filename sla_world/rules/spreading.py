from __future__ import annotations

from typing import Protocol

from sla_world.domain.civilization import Civilization
from sla_world.domain.universe import Universe


class SpreadingRateCalculator(Protocol):
    def calculate(self, civilization: Civilization, universe: Universe) -> float: ...


class ResourceBasedSpreadingRate:
    def calculate(self, civilization: Civilization, universe: Universe) -> float:
        controlled_resources = sum(
            universe.find_system(system_id).resource_summary.total_value()
            for system_id in civilization.controlled_system_ids
        )
        if controlled_resources <= 0.0:
            return 0.0
        utilized_resources = civilization.resources.total_value()
        utilization_ratio = min(utilized_resources / controlled_resources, 1.0)
        return civilization.development.overall_score() * (0.5 + 0.5 * utilization_ratio)
