from __future__ import annotations

from typing import Protocol

from sla_world.simulation.context import StellarTickContext, InterstellarTickContext


class StellarTickHandler(Protocol):
    def execute(self, context: StellarTickContext) -> None: ...


class InterstellarTickHandler(Protocol):
    def execute(self, context: InterstellarTickContext) -> None: ...
