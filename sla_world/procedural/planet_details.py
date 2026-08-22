from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from sla_world.domain.planet import Planet
from sla_world.domain.civilization import Civilization
from sla_world.infrastructure.random import SeededRandom
from sla_world.procedural.cities import City, CityGenerator


class DetailLevel(Enum):
    MINIMAL = auto()
    STANDARD = auto()
    RICH = auto()


@dataclass
class PlanetDetails:
    cities: list[City] = field(default_factory=list)
    population: int = 0
    infrastructure_score: float = 0.0


class PlanetDetailGenerator:
    def __init__(self, city_generator: CityGenerator | None = None) -> None:
        self._city_generator = city_generator or CityGenerator()

    def generate(
        self,
        planet: Planet,
        civilization: Civilization | None,
        detail_level: DetailLevel = DetailLevel.STANDARD,
    ) -> PlanetDetails:
        if planet.control is None or civilization is None:
            return PlanetDetails()
        rng = SeededRandom(planet.id.value)
        cities = self._city_generator.generate(planet, civilization, rng) if detail_level is not DetailLevel.MINIMAL else []
        total_city_population = sum(city.population for city in cities)
        population = total_city_population if cities else int(planet.control.development.population * 1_000_000)
        return PlanetDetails(
            cities=cities,
            population=population,
            infrastructure_score=planet.control.development.infrastructure,
        )
