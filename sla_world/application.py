from __future__ import annotations

from sla_world.domain.universe import Universe
from sla_world.domain.galaxy import Galaxy
from sla_world.domain.system import StarSystem
from sla_world.domain.planet import Planet
from sla_world.domain.civilization import Civilization
from sla_world.domain.war import War
from sla_world.infrastructure.ids import IdSequence, SystemId, StellarObjectId, CivilizationId
from sla_world.rules.spreading import SpreadingRateCalculator, ResourceBasedSpreadingRate
from sla_world.config.simulation import SimulationConfig
from sla_world.simulation.engine import SimulationEngine, SimulationRun
from sla_world.procedural.planet_details import PlanetDetailGenerator, PlanetDetails, DetailLevel
from sla_world.procedural.traffic import TrafficEstimator, TrafficProfile


class DetailServices:
    def __init__(
        self,
        universe: Universe,
        planet_detail_generator: PlanetDetailGenerator | None = None,
        traffic_estimator: TrafficEstimator | None = None,
    ) -> None:
        self._universe = universe
        self._planet_detail_generator = planet_detail_generator or PlanetDetailGenerator()
        self._traffic_estimator = traffic_estimator or TrafficEstimator()

    def for_planet(self, planet: Planet, detail_level: DetailLevel = DetailLevel.STANDARD) -> PlanetDetails:
        civilization = self._universe.civilization(planet.owner) if planet.owner is not None else None
        return self._planet_detail_generator.generate(planet, civilization, detail_level)

    def traffic_for(self, system: StarSystem) -> TrafficProfile:
        return self._traffic_estimator.estimate(system, self._universe)


class World:
    def __init__(
        self,
        universe: Universe,
        id_sequence: IdSequence,
        seed: int,
        spreading_rate_calculator: SpreadingRateCalculator | None = None,
    ) -> None:
        self.universe = universe
        self.id_sequence = id_sequence
        self.seed = seed
        self._spreading_rate_calculator = spreading_rate_calculator or ResourceBasedSpreadingRate()
        self.details = DetailServices(universe)

    @property
    def galaxy(self) -> Galaxy:
        return self.universe.galaxy()

    def systems(self) -> list[StarSystem]:
        return self.universe.systems()

    def planets(self) -> list[Planet]:
        return self.universe.planets()

    def civilizations(self) -> list[Civilization]:
        return self.universe.civilizations

    def find_system(self, system_id: SystemId) -> StarSystem:
        return self.universe.find_system(system_id)

    def find_planet(self, planet_id: StellarObjectId) -> Planet:
        return self.universe.find_planet(planet_id)

    def civilization(self, civilization_id: CivilizationId) -> Civilization:
        return self.universe.civilization(civilization_id)

    def controlled_systems(self, civilization: Civilization) -> list[StarSystem]:
        return [self.universe.find_system(system_id) for system_id in civilization.controlled_system_ids]

    def controlled_planets(self, civilization: Civilization) -> list[Planet]:
        return [self.universe.find_planet(planet_id) for planet_id in civilization.controlled_planet_ids]

    def origin_world(self, civilization: Civilization) -> Planet:
        return self.universe.find_planet(civilization.origin_world_id)

    def spreading_power(self, civilization: Civilization) -> float:
        return self._spreading_rate_calculator.calculate(civilization, self.universe)

    def wars_involving(self, civilization: Civilization) -> list[War]:
        return [self.universe.find_war(war_id) for war_id in civilization.active_war_ids]

    def simulation(self, config: SimulationConfig | None = None) -> SimulationRun:
        config = config or SimulationConfig.standard()
        engine = SimulationEngine.standard(self.id_sequence)
        return SimulationRun(engine=engine, universe=self.universe, config=config, seed=self.seed)
