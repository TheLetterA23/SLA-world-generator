from __future__ import annotations

from dataclasses import dataclass

from sla_world.domain.planet import Planet
from sla_world.domain.civilization import Civilization
from sla_world.infrastructure.random import RandomSource


@dataclass(frozen=True, slots=True)
class City:
    name: str
    population: int
    technology_level: float
    infrastructure_score: float


class CityGenerator:
    def generate(self, planet: Planet, civilization: Civilization, rng: RandomSource) -> list[City]:
        if planet.control is None:
            return []
        development = planet.control.development
        city_count = max(1, round(development.urbanization * 8))
        cities: list[City] = []
        for index in range(city_count):
            weight = rng.uniform(0.4, 1.0)
            population = int(development.population * weight * 1_000_000)
            cities.append(
                City(
                    name=f"{planet.name} City {index + 1}",
                    population=population,
                    technology_level=civilization.development.technology,
                    infrastructure_score=development.infrastructure * weight,
                )
            )
        return cities
