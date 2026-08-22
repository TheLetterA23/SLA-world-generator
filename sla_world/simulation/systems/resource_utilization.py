from __future__ import annotations

from sla_world.simulation.context import StellarTickContext


class ResourceUtilizationHandler:
    def __init__(self, utilization_rate: float = 0.02) -> None:
        self._utilization_rate = utilization_rate

    def execute(self, context: StellarTickContext) -> None:
        for civilization in context.universe.civilizations:
            for system_id in civilization.controlled_system_ids:
                system = context.universe.find_system(system_id)
                for resource, quantity in system.resource_summary.amounts.items():
                    extracted = quantity * self._utilization_rate
                    civilization.resources = civilization.resources.add(resource, extracted)
