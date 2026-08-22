from __future__ import annotations

from typing import Protocol

from sla_world.infrastructure.ids import IdSequence, CivilizationId
from sla_world.infrastructure.random import RandomSource
from sla_world.domain.galaxy import Galaxy
from sla_world.domain.system import StarSystem
from sla_world.domain.planet import Planet, Control
from sla_world.domain.civilization import Civilization
from sla_world.domain.values import SimulationTime
from sla_world.config.generation import CivilizationSeedConfig

_CIVILIZATION_NAME_PREFIXES = ("Zeth", "Kaon", "Thal", "Vor", "Nym", "Sera", "Or", "Il", "Kry", "Ash")
_CIVILIZATION_NAME_SUFFIXES = ("ari", "on", "ese", "ians", "yn", "ak", "ora", "eth")


def generate_civilization_name(rng: RandomSource) -> str:
    return f"{rng.choice(_CIVILIZATION_NAME_PREFIXES)}{rng.choice(_CIVILIZATION_NAME_SUFFIXES)}"


class CivilizationSeedStrategy(Protocol):
    def choose_origin_systems(self, galaxy: Galaxy, count: int, rng: RandomSource) -> list[StarSystem]: ...


class ScatteredOriginSelection:
    def choose_origin_systems(self, galaxy: Galaxy, count: int, rng: RandomSource) -> list[StarSystem]:
        eligible = [system for system in galaxy.all_systems() if system.habitable_planets()]
        return rng.sample(eligible, min(count, len(eligible)))


class CivilizationSeeder:
    def __init__(self, strategy: CivilizationSeedStrategy | None = None) -> None:
        self._strategy = strategy or ScatteredOriginSelection()

    def seed(
        self, galaxy: Galaxy, config: CivilizationSeedConfig, id_sequence: IdSequence, rng: RandomSource
    ) -> list[Civilization]:
        origin_systems = self._strategy.choose_origin_systems(galaxy, config.civilization_count, rng)
        civilizations: list[Civilization] = []
        for system in origin_systems:
            origin_planet = self._choose_origin_planet(system, config, rng)
            if origin_planet is None:
                continue
            civilization = Civilization(
                id=CivilizationId(id_sequence.next()),
                name=generate_civilization_name(rng),
                origin_world_id=origin_planet.id,
            )
            origin_planet.control = Control(civilization_id=civilization.id, established_at=SimulationTime(0))
            civilization.controlled_planet_ids.add(origin_planet.id)
            civilization.controlled_system_ids.add(system.id)
            system.controlled_by = civilization.id
            civilizations.append(civilization)
        return civilizations

    def _choose_origin_planet(
        self, system: StarSystem, config: CivilizationSeedConfig, rng: RandomSource
    ) -> Planet | None:
        candidates = [
            planet for planet in system.habitable_planets()
            if planet.habitability.base_score >= config.minimum_origin_habitability
        ]
        if not candidates:
            candidates = system.habitable_planets()
        if not candidates:
            return None
        return max(candidates, key=lambda planet: planet.habitability.base_score)
