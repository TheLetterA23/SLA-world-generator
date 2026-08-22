from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CivilizationDevelopment:
    technology: float = 1.0
    industrialization: float = 1.0
    infrastructure: float = 1.0
    population: float = 1.0

    def overall_score(self) -> float:
        return (self.technology + self.industrialization + self.infrastructure + self.population) / 4.0
