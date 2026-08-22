from __future__ import annotations

from dataclasses import dataclass, field

from sla_world.infrastructure.ids import SystemId, ConnectionId
from sla_world.domain.system import StarSystem
from sla_world.domain.connection import Connection


@dataclass
class Galaxy:
    systems: dict[SystemId, StarSystem] = field(default_factory=dict)
    connections: dict[ConnectionId, Connection] = field(default_factory=dict)

    def system(self, system_id: SystemId) -> StarSystem:
        return self.systems[system_id]

    def all_systems(self) -> list[StarSystem]:
        return list(self.systems.values())

    def add_system(self, system: StarSystem) -> None:
        self.systems[system.id] = system

    def add_connection(self, connection: Connection) -> None:
        self.connections[connection.id] = connection
        self.systems[connection.a].connection_ids.add(connection.id)
        self.systems[connection.b].connection_ids.add(connection.id)

    def connections_for(self, system: StarSystem) -> list[Connection]:
        return [self.connections[connection_id] for connection_id in system.connection_ids]

    def neighbors(self, system: StarSystem) -> list[StarSystem]:
        return [self.systems[connection.other(system.id)] for connection in self.connections_for(system)]

    def distance(self, a: StarSystem, b: StarSystem) -> float:
        return a.position.distance_to(b.position)

    def nearby(self, system: StarSystem, max_distance: float) -> list[StarSystem]:
        return [
            other
            for other in self.systems.values()
            if other.id != system.id and self.distance(system, other) <= max_distance
        ]
