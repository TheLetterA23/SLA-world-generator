from __future__ import annotations

from dataclasses import dataclass, field

from sla_world.infrastructure.ids import SystemId, StellarObjectId, CivilizationId
from sla_world.domain.galaxy import Galaxy
from sla_world.domain.system import StarSystem
from sla_world.domain.planet import Planet
from sla_world.domain.civilization import Civilization


@dataclass
class Universe:
    galaxies: list[Galaxy] = field(default_factory=list)
    civilizations: list[Civilization] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.reindex()

    def reindex(self) -> None:
        self._systems_by_id: dict[SystemId, StarSystem] = {}
        self._planets_by_id: dict[StellarObjectId, Planet] = {}
        self._civilizations_by_id: dict[CivilizationId, Civilization] = {}
        for galaxy in self.galaxies:
            for system in galaxy.all_systems():
                self._systems_by_id[system.id] = system
                for planet in system.planets():
                    self._planets_by_id[planet.id] = planet
        for civilization in self.civilizations:
            self._civilizations_by_id[civilization.id] = civilization

    def find_system(self, system_id: SystemId) -> StarSystem:
        return self._systems_by_id[system_id]

    def find_planet(self, planet_id: StellarObjectId) -> Planet:
        return self._planets_by_id[planet_id]

    def civilization(self, civilization_id: CivilizationId) -> Civilization:
        return self._civilizations_by_id[civilization_id]

    def systems(self) -> list[StarSystem]:
        return list(self._systems_by_id.values())

    def planets(self) -> list[Planet]:
        return list(self._planets_by_id.values())

    def galaxy(self) -> Galaxy:
        return self.galaxies[0]
