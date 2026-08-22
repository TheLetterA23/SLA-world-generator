from __future__ import annotations

from typing import Callable

from sla_world.infrastructure.ids import IdSequence
from sla_world.infrastructure.random import RandomStreams
from sla_world.domain.universe import Universe
from sla_world.config.generation import WorldGenerationConfig, SystemGenerationConfig
from sla_world.generation.star_map_generator import StarMapGenerator
from sla_world.generation.system_generator import SystemGenerator
from sla_world.generation.connection_generator import ConnectionGenerator
from sla_world.generation.civilization_seeder import CivilizationSeeder
from sla_world.application import World


class WorldBuilder:
    def __init__(
        self,
        star_map_generator: StarMapGenerator | None = None,
        system_generator_factory: Callable[[SystemGenerationConfig], SystemGenerator] = SystemGenerator,
        connection_generator: ConnectionGenerator | None = None,
        civilization_seeder: CivilizationSeeder | None = None,
    ) -> None:
        self._star_map_generator = star_map_generator or StarMapGenerator()
        self._system_generator_factory = system_generator_factory
        self._connection_generator = connection_generator or ConnectionGenerator()
        self._civilization_seeder = civilization_seeder or CivilizationSeeder()
        self._seed = 0

    @staticmethod
    def default() -> "WorldBuilder":
        return WorldBuilder()

    def with_seed(self, seed: int) -> "WorldBuilder":
        self._seed = seed
        return self

    def build(self, config: WorldGenerationConfig | None = None) -> World:
        config = config or WorldGenerationConfig.default()
        streams = RandomStreams(self._seed)
        id_sequence = IdSequence()

        galaxy = self._star_map_generator.generate(config.stars, id_sequence, streams.stream("generation.star_map"))

        system_generator = self._system_generator_factory(config.systems)
        system_rng = streams.stream("generation.systems")
        for system in galaxy.all_systems():
            system_generator.generate(system, id_sequence, system_rng)

        self._connection_generator.generate(
            galaxy, config.connections, id_sequence, streams.stream("generation.connections")
        )

        civilizations = self._civilization_seeder.seed(
            galaxy, config.civilizations, id_sequence, streams.stream("generation.civilizations")
        )

        universe = Universe(galaxies=[galaxy], civilizations=civilizations)
        return World(universe=universe, id_sequence=id_sequence, seed=self._seed)
