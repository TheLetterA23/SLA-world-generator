from __future__ import annotations

from dataclasses import dataclass

from sla_world.infrastructure.ids import WarId, CivilizationId
from sla_world.domain.values import SimulationTime


@dataclass
class War:
    id: WarId
    attacker_id: CivilizationId
    defender_id: CivilizationId
    started_at: SimulationTime
    attacker_exhaustion: float = 0.0
    defender_exhaustion: float = 0.0
    active: bool = True

    def involves(self, civilization_id: CivilizationId) -> bool:
        return civilization_id in (self.attacker_id, self.defender_id)

    def opponent_of(self, civilization_id: CivilizationId) -> CivilizationId:
        return self.defender_id if civilization_id == self.attacker_id else self.attacker_id

    def exhaustion_for(self, civilization_id: CivilizationId) -> float:
        return self.attacker_exhaustion if civilization_id == self.attacker_id else self.defender_exhaustion

    def add_exhaustion(self, civilization_id: CivilizationId, amount: float) -> None:
        if civilization_id == self.attacker_id:
            self.attacker_exhaustion += amount
        else:
            self.defender_exhaustion += amount
