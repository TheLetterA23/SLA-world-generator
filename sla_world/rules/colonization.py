from __future__ import annotations

from typing import Protocol

from sla_world.domain.planet import Planet
from sla_world.domain.system import StarSystem
from sla_world.domain.civilization import Civilization
from sla_world.domain.universe import Universe
from sla_world.rules.habitability import HabitabilityEvaluator


class ColonizationTargetSelector(Protocol):
    def choose(self, civilization: Civilization, system: StarSystem, universe: Universe) -> Planet | None: ...


class MostHabitableRelativeToOrigin:
    def __init__(self, evaluator: HabitabilityEvaluator | None = None) -> None:
        self._evaluator = evaluator or HabitabilityEvaluator()

    def choose(self, civilization: Civilization, system: StarSystem, universe: Universe) -> Planet | None:
        candidates = [planet for planet in system.planets() if planet.owner is None]
        if not candidates:
            return None
        return max(candidates, key=lambda planet: self._evaluator.score(planet, civilization, universe))
