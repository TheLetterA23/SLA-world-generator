from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Mapping

from sla_world.infrastructure.ids import CivilizationId, StellarObjectId, SystemId, WarId
from sla_world.domain.resources import ResourceInventory
from sla_world.domain.development import CivilizationDevelopment
from sla_world.domain.trade import TradeState
from sla_world.domain.values import SimulationTime


@dataclass(frozen=True, slots=True)
class SimulationEvent:
    time: SimulationTime
    kind: str
    actor_id: str
    data: Mapping[str, object] = field(default_factory=dict)


@dataclass
class CivilizationHistory:
    events: list[SimulationEvent] = field(default_factory=list)

    def record(self, event: SimulationEvent) -> None:
        self.events.append(event)

    def events_of_kind(self, kind: str) -> list[SimulationEvent]:
        return [event for event in self.events if event.kind == kind]


class DiplomaticStance(Enum):
    NEUTRAL = auto()
    WAR = auto()
    ALLIANCE = auto()


@dataclass
class DiplomacyState:
    relations: dict[CivilizationId, DiplomaticStance] = field(default_factory=dict)

    def stance_with(self, other: CivilizationId) -> DiplomaticStance:
        return self.relations.get(other, DiplomaticStance.NEUTRAL)

    def is_at_war_with(self, other: CivilizationId) -> bool:
        return self.stance_with(other) is DiplomaticStance.WAR

    def is_allied_with(self, other: CivilizationId) -> bool:
        return self.stance_with(other) is DiplomaticStance.ALLIANCE

    def set_stance(self, other: CivilizationId, stance: DiplomaticStance) -> None:
        self.relations[other] = stance


@dataclass
class Civilization:
    id: CivilizationId
    name: str
    origin_world_id: StellarObjectId
    controlled_system_ids: set[SystemId] = field(default_factory=set)
    controlled_planet_ids: set[StellarObjectId] = field(default_factory=set)
    resources: ResourceInventory = field(default_factory=ResourceInventory.empty)
    development: CivilizationDevelopment = field(default_factory=CivilizationDevelopment)
    history: CivilizationHistory = field(default_factory=CivilizationHistory)
    diplomacy: DiplomacyState = field(default_factory=DiplomacyState)
    trade: TradeState = field(default_factory=TradeState)
    active_war_ids: set[WarId] = field(default_factory=set)

    def is_at_war_with(self, other: "Civilization") -> bool:
        return self.diplomacy.is_at_war_with(other.id)

    def is_allied_with(self, other: "Civilization") -> bool:
        return self.diplomacy.is_allied_with(other.id)

    def can_afford(self, cost: ResourceInventory) -> bool:
        return self.resources.covers(cost)
