from __future__ import annotations

from dataclasses import dataclass

from sla_world.domain.values import SimulationTime, Duration


@dataclass
class SimulationClock:
    current_time: SimulationTime = SimulationTime(0)
    stellar_interval: Duration = Duration(1)
    interstellar_interval: Duration = Duration(100)

    def advance_stellar(self) -> None:
        self.current_time = SimulationTime(self.current_time + self.stellar_interval)

    def advance_interstellar(self) -> None:
        self.current_time = SimulationTime(self.current_time + self.interstellar_interval)
