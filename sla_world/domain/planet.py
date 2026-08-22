from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from sla_world.infrastructure.ids import StellarObjectId, SystemId, CivilizationId
from sla_world.domain.stellar_objects import StellarObject
from sla_world.domain.values import SimulationTime


class PlanetType(Enum):
    ROCKY = auto()
    OCEAN = auto()
    ICE = auto()
    GAS_GIANT = auto()
    DESERT = auto()
    VOLCANIC = auto()
    BARREN = auto()


@dataclass(frozen=True, slots=True)
class Atmosphere:
    density: float
    breathable: bool
    composition: str


@dataclass(frozen=True, slots=True)
class HabitabilityProfile:
    temperature_score: float
    atmosphere_score: float
    water_score: float
    biosphere_score: float

    @property
    def base_score(self) -> float:
        return (self.temperature_score + self.atmosphere_score + self.water_score + self.biosphere_score) / 4.0


@dataclass
class PlanetDevelopment:
    population: float = 0.0
    infrastructure: float = 0.0
    industry: float = 0.0
    urbanization: float = 0.0


@dataclass
class Control:
    civilization_id: CivilizationId
    established_at: SimulationTime
    development: PlanetDevelopment = field(default_factory=PlanetDevelopment)


def _default_atmosphere() -> Atmosphere:
    return Atmosphere(density=0.0, breathable=False, composition="none")


def _default_habitability() -> HabitabilityProfile:
    return HabitabilityProfile(0.0, 0.0, 0.0, 0.0)


@dataclass
class Planet(StellarObject):
    planet_type: PlanetType = PlanetType.ROCKY
    atmosphere: Atmosphere = field(default_factory=_default_atmosphere)
    habitability: HabitabilityProfile = field(default_factory=_default_habitability)
    parent_system_id: SystemId | None = None
    moon_ids: list[StellarObjectId] = field(default_factory=list)
    control: Control | None = None

    def is_habitable(self, threshold: float = 0.5) -> bool:
        return self.habitability.base_score >= threshold

    @property
    def owner(self) -> CivilizationId | None:
        return self.control.civilization_id if self.control is not None else None

    @property
    def development(self) -> PlanetDevelopment | None:
        return self.control.development if self.control is not None else None

    @property
    def development_level(self) -> float:
        if self.control is None:
            return 0.0
        development = self.control.development
        return (development.population + development.infrastructure + development.industry + development.urbanization) / 4.0
