from __future__ import annotations

from sla_world.domain.planet import Planet
from sla_world.domain.civilization import Civilization
from sla_world.domain.universe import Universe


class HabitabilityEvaluator:
    def score(self, planet: Planet, civilization: Civilization, universe: Universe) -> float:
        origin_planet = universe.find_planet(civilization.origin_world_id)
        base = planet.habitability.base_score
        similarity = 1.0 - abs(planet.habitability.base_score - origin_planet.habitability.base_score)
        return (base * 0.7) + (similarity * 0.3)
