from __future__ import annotations

from dataclasses import dataclass, field

from sla_world.infrastructure.ids import StellarObjectId
from sla_world.domain.resources import ResourceInventory


@dataclass
class StellarObject:
    id: StellarObjectId
    name: str
    mass: float | None
    radius: float | None
    resources: ResourceInventory = field(default_factory=ResourceInventory.empty)

    def resource_value(self) -> float:
        return self.resources.total_value()


@dataclass
class Star(StellarObject):
    spectral_class: str = "G"
    luminosity: float = 1.0


@dataclass
class Moon(StellarObject):
    parent_planet_id: StellarObjectId | None = None


@dataclass
class AsteroidBelt(StellarObject):
    density: float = 1.0


@dataclass
class Nebula(StellarObject):
    composition: str = "gas"


@dataclass
class BlackHole(StellarObject):
    event_horizon_radius: float = 0.0
