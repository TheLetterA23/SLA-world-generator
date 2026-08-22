from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar

from sla_world.infrastructure.ids import SystemId, ConnectionId, CivilizationId, StellarObjectId
from sla_world.domain.values import Position
from sla_world.domain.stellar_objects import StellarObject, Star, Moon, AsteroidBelt
from sla_world.domain.planet import Planet
from sla_world.domain.resources import ResourceInventory

T = TypeVar("T", bound=StellarObject)


@dataclass
class StarSystem:
    id: SystemId
    name: str
    position: Position
    stars: list[Star] = field(default_factory=list)
    objects: list[StellarObject] = field(default_factory=list)
    connection_ids: set[ConnectionId] = field(default_factory=set)
    resource_summary: ResourceInventory = field(default_factory=ResourceInventory.empty)
    controlled_by: CivilizationId | None = None

    def objects_of_type(self, object_type: type[T]) -> list[T]:
        return [stellar_object for stellar_object in self.objects if isinstance(stellar_object, object_type)]

    def planets(self) -> list[Planet]:
        return self.objects_of_type(Planet)

    def moons(self) -> list[Moon]:
        return self.objects_of_type(Moon)

    def asteroid_belts(self) -> list[AsteroidBelt]:
        return self.objects_of_type(AsteroidBelt)

    def habitable_planets(self, threshold: float = 0.5) -> list[Planet]:
        return [planet for planet in self.planets() if planet.is_habitable(threshold)]

    def find_planet(self, planet_id: StellarObjectId) -> Planet | None:
        for planet in self.planets():
            if planet.id == planet_id:
                return planet
        return None

    def is_controlled(self) -> bool:
        return self.controlled_by is not None
