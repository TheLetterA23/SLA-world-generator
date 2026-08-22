from __future__ import annotations

from dataclasses import dataclass, field

from sla_world.domain.universe import Universe
from sla_world.domain.values import SimulationTime
from sla_world.infrastructure.ids import IdSequence
from sla_world.infrastructure.random import RandomStreams, SeededRandom
from sla_world.simulation.clock import SimulationClock
from sla_world.simulation.context import StellarTickContext, InterstellarTickContext
from sla_world.simulation.ticks import StellarTickHandler, InterstellarTickHandler
from sla_world.simulation.systems.resource_utilization import ResourceUtilizationHandler
from sla_world.simulation.systems.colonization import LocalColonizationHandler
from sla_world.simulation.systems.exploration import ExplorationHandler
from sla_world.simulation.systems.development import PlanetaryDevelopmentHandler
from sla_world.simulation.interstellar.expansion import ExpansionHandler
from sla_world.simulation.interstellar.trading import TradeRouteHandler
from sla_world.config.simulation import SimulationConfig
from sla_world.rules.consistency import UniverseValidator


@dataclass
class SimulationEngine:
    stellar_handlers: list[StellarTickHandler] = field(default_factory=list)
    interstellar_handlers: list[InterstellarTickHandler] = field(default_factory=list)

    @staticmethod
    def standard(id_sequence: IdSequence) -> "SimulationEngine":
        return SimulationEngine(
            stellar_handlers=[
                ResourceUtilizationHandler(),
                PlanetaryDevelopmentHandler(),
                LocalColonizationHandler(),
                ExplorationHandler(),
            ],
            interstellar_handlers=[
                ExpansionHandler(),
                TradeRouteHandler(id_sequence),
            ],
        )

    def step_stellar(self, universe: Universe, clock: SimulationClock, rng: SeededRandom) -> None:
        context = StellarTickContext(universe=universe, clock=clock, rng=rng)
        for handler in self.stellar_handlers:
            handler.execute(context)

    def step_interstellar(self, universe: Universe, clock: SimulationClock, rng: SeededRandom) -> None:
        context = InterstellarTickContext(universe=universe, clock=clock, rng=rng)
        for handler in self.interstellar_handlers:
            handler.execute(context)


class SimulationRun:
    def __init__(self, engine: SimulationEngine, universe: Universe, config: SimulationConfig, seed: int) -> None:
        self._engine = engine
        self._universe = universe
        self._config = config
        self._validator = UniverseValidator() if config.validate_after_tick else None
        self.clock = SimulationClock(
            current_time=SimulationTime(0),
            stellar_interval=config.stellar_tick_length,
            interstellar_interval=config.interstellar_tick_length,
        )
        streams = RandomStreams(seed)
        self._stellar_rng = streams.stream("simulation.stellar")
        self._interstellar_rng = streams.stream("simulation.interstellar")

    def run(self, until: int) -> None:
        steps_per_interstellar = max(1, self._config.interstellar_tick_length // self._config.stellar_tick_length)
        step_index = 0
        while self.clock.current_time < until:
            self._engine.step_stellar(self._universe, self.clock, self._stellar_rng)
            self.clock.advance_stellar()
            step_index += 1
            if step_index % steps_per_interstellar == 0:
                self._engine.step_interstellar(self._universe, self.clock, self._interstellar_rng)
            self._validate_if_configured()

    def _validate_if_configured(self) -> None:
        if self._validator is None:
            return
        report = self._validator.validate(self._universe)
        if not report.is_valid:
            raise RuntimeError(f"Universe invariants violated at time {self.clock.current_time}: {report.issues}")
