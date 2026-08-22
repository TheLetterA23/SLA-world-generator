from __future__ import annotations

from typing import Protocol

from sla_world.infrastructure.ids import IdSequence, SystemId
from sla_world.infrastructure.random import RandomSource
from sla_world.domain.values import Position
from sla_world.domain.galaxy import Galaxy
from sla_world.domain.system import StarSystem
from sla_world.config.generation import StarMapConfig

_SYSTEM_NAME_SYLLABLES = (
    "Ax", "Bel", "Cor", "Dra", "El", "Fen", "Gor", "Hy", "Il", "Jax",
    "Ky", "Lor", "Mir", "Nex", "Or", "Pyr", "Quor", "Rho", "Sol", "Tor",
    "Uri", "Vex", "Wyn", "Xen", "Yl", "Zor",
)


class SpatialDistribution(Protocol):
    def position_for(self, index: int, config: StarMapConfig, rng: RandomSource) -> Position: ...


class UniformDistribution:
    def position_for(self, index: int, config: StarMapConfig, rng: RandomSource) -> Position:
        return Position(
            x=rng.uniform(0.0, config.width),
            y=rng.uniform(0.0, config.height),
            z=rng.uniform(0.0, config.depth) if config.depth > 0.0 else 0.0,
        )


def generate_system_name(rng: RandomSource) -> str:
    syllable_count = rng.randint(2, 3)
    return "".join(rng.choice(_SYSTEM_NAME_SYLLABLES) for _ in range(syllable_count))


class StarMapGenerator:
    def __init__(self, distribution: SpatialDistribution | None = None) -> None:
        self._distribution = distribution or UniformDistribution()

    def generate(self, config: StarMapConfig, id_sequence: IdSequence, rng: RandomSource) -> Galaxy:
        galaxy = Galaxy()
        for index in range(config.star_count):
            position = self._distribution.position_for(index, config, rng)
            system = StarSystem(
                id=SystemId(id_sequence.next()),
                name=generate_system_name(rng),
                position=position,
            )
            galaxy.add_system(system)
        return galaxy
