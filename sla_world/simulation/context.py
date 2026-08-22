from __future__ import annotations

from dataclasses import dataclass

from sla_world.domain.universe import Universe
from sla_world.infrastructure.random import RandomSource
from sla_world.simulation.clock import SimulationClock


@dataclass
class StellarTickContext:
    universe: Universe
    clock: SimulationClock
    rng: RandomSource


@dataclass
class InterstellarTickContext:
    universe: Universe
    clock: SimulationClock
    rng: RandomSource
