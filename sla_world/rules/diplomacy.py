from __future__ import annotations

from typing import Protocol

from sla_world.domain.civilization import Civilization
from sla_world.domain.war import War
from sla_world.domain.universe import Universe
from sla_world.rules.spreading import SpreadingRateCalculator, ResourceBasedSpreadingRate


class WarDeclarationPolicy(Protocol):
    def should_declare_war(self, civilization: Civilization, other: Civilization, universe: Universe) -> bool: ...


class PeacePolicy(Protocol):
    def should_seek_peace(self, civilization: Civilization, war: War, universe: Universe) -> bool: ...


class AlliancePolicy(Protocol):
    def should_propose_alliance(self, civilization: Civilization, other: Civilization, universe: Universe) -> bool: ...


class SpreadingPowerWarPolicy:
    def __init__(
        self, spreading_rate_calculator: SpreadingRateCalculator | None = None, aggression_ratio: float = 1.5
    ) -> None:
        self._spreading_rate_calculator = spreading_rate_calculator or ResourceBasedSpreadingRate()
        self._aggression_ratio = aggression_ratio

    def should_declare_war(self, civilization: Civilization, other: Civilization, universe: Universe) -> bool:
        own_power = self._spreading_rate_calculator.calculate(civilization, universe)
        their_power = self._spreading_rate_calculator.calculate(other, universe)
        return own_power > their_power * self._aggression_ratio


class ExhaustionPeacePolicy:
    def __init__(self, exhaustion_threshold: float = 0.7) -> None:
        self._exhaustion_threshold = exhaustion_threshold

    def should_seek_peace(self, civilization: Civilization, war: War, universe: Universe) -> bool:
        return war.exhaustion_for(civilization.id) >= self._exhaustion_threshold


class SimilarDevelopmentAlliancePolicy:
    def __init__(self, similarity_tolerance: float = 0.2) -> None:
        self._similarity_tolerance = similarity_tolerance

    def should_propose_alliance(self, civilization: Civilization, other: Civilization, universe: Universe) -> bool:
        difference = abs(civilization.development.overall_score() - other.development.overall_score())
        return difference <= self._similarity_tolerance
