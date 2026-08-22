from __future__ import annotations

from dataclasses import dataclass

from sla_world.infrastructure.ids import ConnectionId, SystemId


@dataclass(frozen=True, slots=True)
class Connection:
    id: ConnectionId
    a: SystemId
    b: SystemId
    distance: float
    travel_cost: float

    def other(self, system_id: SystemId) -> SystemId:
        if system_id == self.a:
            return self.b
        if system_id == self.b:
            return self.a
        raise ValueError(f"Connection {self.id} does not touch system {system_id}")

    def connects(self, system_id: SystemId) -> bool:
        return system_id in (self.a, self.b)
