from __future__ import annotations

from sla_world.simulation.context import InterstellarTickContext
from sla_world.rules.trade import TradeRoutePolicy, NeighboringSystemTradePolicy
from sla_world.infrastructure.ids import IdSequence


class TradeRouteHandler:
    def __init__(self, id_sequence: IdSequence, policy: TradeRoutePolicy | None = None) -> None:
        self._id_sequence = id_sequence
        self._policy = policy or NeighboringSystemTradePolicy()

    def execute(self, context: InterstellarTickContext) -> None:
        for civilization in context.universe.civilizations:
            self._policy.update_routes(civilization, context.universe, self._id_sequence)
