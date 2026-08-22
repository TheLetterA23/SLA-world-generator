from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StarMapConfig:
    star_count: int
    width: float
    height: float
    depth: float = 0.0


@dataclass(frozen=True)
class SystemGenerationConfig:
    min_planets: int = 0
    max_planets: int = 8
    min_moons_per_planet: int = 0
    max_moons_per_planet: int = 3
    asteroid_belt_chance: float = 0.2
    resource_richness: float = 1.0


@dataclass(frozen=True)
class ConnectionConfig:
    density: float
    max_distance: float
    minimum_connections: int = 1


@dataclass(frozen=True)
class CivilizationSeedConfig:
    civilization_count: int
    minimum_origin_habitability: float = 0.6


@dataclass(frozen=True)
class WorldGenerationConfig:
    stars: StarMapConfig
    systems: SystemGenerationConfig
    connections: ConnectionConfig
    civilizations: CivilizationSeedConfig

    @staticmethod
    def default() -> "WorldGenerationConfig":
        return WorldGenerationConfig(
            stars=StarMapConfig(star_count=200, width=500.0, height=500.0, depth=500.0),
            systems=SystemGenerationConfig(),
            connections=ConnectionConfig(density=0.05, max_distance=80.0),
            civilizations=CivilizationSeedConfig(civilization_count=6),
        )
