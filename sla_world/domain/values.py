from __future__ import annotations

from dataclasses import dataclass
from typing import NewType

SimulationTime = NewType("SimulationTime", int)
Duration = NewType("Duration", int)


@dataclass(frozen=True, slots=True)
class Position:
    x: float
    y: float
    z: float = 0.0

    def distance_to(self, other: "Position") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2) ** 0.5
