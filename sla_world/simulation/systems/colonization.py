from __future__ import annotations

from sla_world.simulation.context import StellarTickContext
from sla_world.rules.colonization import ColonizationTargetSelector, MostHabitableRelativeToOrigin
from sla_world.rules.colonization_cost import ColonizationCostCalculator, FlatColonizationCost, HabitabilityScaledCost
from sla_world.domain.planet import Control
from sla_world.domain.civilization import SimulationEvent


class LocalColonizationHandler:
    def __init__(
        self,
        target_selector: ColonizationTargetSelector | None = None,
        cost_calculator: ColonizationCostCalculator | None = None,
    ) -> None:
        self._target_selector = target_selector or MostHabitableRelativeToOrigin()
        self._cost_calculator = cost_calculator or HabitabilityScaledCost()

    def execute(self, context: StellarTickContext) -> None:
        for civilization in context.universe.civilizations:
            for system_id in list(civilization.controlled_system_ids):
                system = context.universe.find_system(system_id)
                target = self._target_selector.choose(civilization, system, context.universe)
                if target is None:
                    continue
                cost = self._cost_calculator.cost_for(civilization, target)
                if not civilization.can_afford(cost):
                    continue
                civilization.resources = civilization.resources.subtract(cost)
                target.control = Control(civilization_id=civilization.id, established_at=context.clock.current_time)
                civilization.controlled_planet_ids.add(target.id)
                civilization.history.record(
                    SimulationEvent(
                        time=context.clock.current_time,
                        kind="PlanetColonized",
                        actor_id=str(civilization.id.value),
                        data={
                            "planet_id": target.id.value,
                            "system_id": system.id.value,
                            "cost": {resource.name: quantity for resource, quantity in cost.amounts.items()},
                        },
                    )
                )
