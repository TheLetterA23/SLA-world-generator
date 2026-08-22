from __future__ import annotations

from sla_world.simulation.context import StellarTickContext


class PlanetaryDevelopmentHandler:
    def __init__(self, growth_rate: float = 0.01) -> None:
        self._growth_rate = growth_rate

    def execute(self, context: StellarTickContext) -> None:
        for civilization in context.universe.civilizations:
            for planet_id in civilization.controlled_planet_ids:
                planet = context.universe.find_planet(planet_id)
                if planet.control is None:
                    continue
                self._grow(planet.control.development, planet.habitability.base_score, civilization.development)

    def _grow(self, development, habitability: float, civilization_development) -> None:
        development.population = min(1.0, development.population + self._growth_rate * (0.2 + habitability))
        development.infrastructure = min(1.0, development.infrastructure + self._growth_rate * civilization_development.infrastructure * 0.1)
        development.industry = min(1.0, development.industry + self._growth_rate * civilization_development.industrialization * 0.1)
        development.urbanization = min(1.0, development.urbanization + self._growth_rate * 0.5)
