from __future__ import annotations

from dataclasses import dataclass

from sla_world import World, WorldBuilder, SimulationConfig, WorldGenerationConfig
from sla_world.config.generation import StarMapConfig, SystemGenerationConfig, ConnectionConfig, CivilizationSeedConfig
from sla_world.domain.civilization import Civilization
from sla_world.domain.system import StarSystem


@dataclass(frozen=True)
class ExplorerSettings:
    seed: int
    ticks: int = 5000
    star_count: int = 200
    civilization_count: int = 6
    width: float = 500.0
    height: float = 500.0
    depth: float = 500.0
    connection_density: float = 0.05
    connection_max_distance: float = 80.0


def _generation_config(settings: ExplorerSettings) -> WorldGenerationConfig:
    return WorldGenerationConfig(
        stars=StarMapConfig(
            star_count=settings.star_count, width=settings.width, height=settings.height, depth=settings.depth
        ),
        systems=SystemGenerationConfig(),
        connections=ConnectionConfig(
            density=settings.connection_density, max_distance=settings.connection_max_distance
        ),
        civilizations=CivilizationSeedConfig(civilization_count=settings.civilization_count),
    )


class SimulationContext:
    def __init__(self, settings: ExplorerSettings) -> None:
        self.settings = settings
        self.world: World = WorldBuilder.default().with_seed(settings.seed).build(_generation_config(settings))
        self.simulated_time = 0
        if settings.ticks > 0:
            simulation = self.world.simulation(SimulationConfig.standard())
            simulation.run(until=settings.ticks)
            self.simulated_time = simulation.clock.current_time

    def civilizations(self) -> list[Civilization]:
        return sorted(self.world.civilizations(), key=lambda civilization: civilization.id.value)

    def systems(self) -> list[StarSystem]:
        return sorted(self.world.systems(), key=lambda system: system.id.value)

    def find_civilization(self, token: str) -> list[Civilization]:
        token = token.strip().lstrip("#")
        if token.isdigit():
            return [c for c in self.world.civilizations() if c.id.value == int(token)]
        lowered = token.lower()
        return [c for c in self.world.civilizations() if c.name.lower() == lowered]

    def find_system(self, token: str) -> list[StarSystem]:
        token = token.strip().lstrip("#")
        if token.isdigit():
            return [s for s in self.world.systems() if s.id.value == int(token)]
        lowered = token.lower()
        return [s for s in self.world.systems() if s.name.lower() == lowered]
