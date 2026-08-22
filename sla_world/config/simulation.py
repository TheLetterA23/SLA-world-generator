from __future__ import annotations

from dataclasses import dataclass

from sla_world.domain.values import Duration


@dataclass(frozen=True)
class SimulationConfig:
    stellar_tick_length: Duration = Duration(1)
    interstellar_tick_length: Duration = Duration(100)
    validate_after_tick: bool = False

    @staticmethod
    def standard() -> "SimulationConfig":
        return SimulationConfig(stellar_tick_length=Duration(1), interstellar_tick_length=Duration(100))
