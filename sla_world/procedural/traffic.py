from __future__ import annotations

from dataclasses import dataclass

from sla_world.domain.system import StarSystem
from sla_world.domain.universe import Universe


@dataclass(frozen=True, slots=True)
class TrafficProfile:
    estimated_ships: int
    congestion: float


class TrafficEstimator:
    def estimate(self, system: StarSystem, universe: Universe) -> TrafficProfile:
        connection_count = len(system.connection_ids)
        base_traffic = system.resource_summary.total_value() * 0.001
        controlled_bonus = 5.0 if system.is_controlled() else 0.0
        estimated_ships = int(base_traffic + connection_count * 2 + controlled_bonus)
        congestion = min(1.0, connection_count / 8.0)
        return TrafficProfile(estimated_ships=estimated_ships, congestion=congestion)
