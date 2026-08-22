from __future__ import annotations

from sla_world.simulation.context import InterstellarTickContext
from sla_world.rules.spreading import SpreadingRateCalculator, ResourceBasedSpreadingRate
from sla_world.domain.civilization import Civilization, SimulationEvent
from sla_world.domain.universe import Universe
from sla_world.domain.system import StarSystem


class ExpansionHandler:
    def __init__(
        self,
        spreading_rate_calculator: SpreadingRateCalculator | None = None,
        expansion_threshold: float = 0.4,
    ) -> None:
        self._spreading_rate_calculator = spreading_rate_calculator or ResourceBasedSpreadingRate()
        self._expansion_threshold = expansion_threshold

    def execute(self, context: InterstellarTickContext) -> None:
        for civilization in context.universe.civilizations:
            rate = self._spreading_rate_calculator.calculate(civilization, context.universe)
            if rate < self._expansion_threshold:
                continue
            frontier = self._frontier_systems(civilization, context.universe)
            if not frontier:
                continue
            target = context.rng.choice(frontier)
            target.controlled_by = civilization.id
            civilization.controlled_system_ids.add(target.id)
            civilization.history.record(
                SimulationEvent(
                    time=context.clock.current_time,
                    kind="SystemClaimed",
                    actor_id=str(civilization.id.value),
                    data={"system_id": target.id.value},
                )
            )

    def _frontier_systems(self, civilization: Civilization, universe: Universe) -> list[StarSystem]:
        galaxy = universe.galaxy()
        frontier_by_id: dict = {}
        for system_id in civilization.controlled_system_ids:
            system = universe.find_system(system_id)
            for neighbor in galaxy.neighbors(system):
                if not neighbor.is_controlled():
                    frontier_by_id[neighbor.id] = neighbor
        return list(frontier_by_id.values())
