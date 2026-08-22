from __future__ import annotations

from typing import Protocol

from sla_world.infrastructure.ids import IdSequence, TradeRouteId
from sla_world.domain.civilization import Civilization
from sla_world.domain.universe import Universe
from sla_world.domain.trade import TradeRoute


class TradeRoutePolicy(Protocol):
    def update_routes(self, civilization: Civilization, universe: Universe, id_sequence: IdSequence) -> list[TradeRoute]: ...


class NeighboringSystemTradePolicy:
    def update_routes(self, civilization: Civilization, universe: Universe, id_sequence: IdSequence) -> list[TradeRoute]:
        galaxy = universe.galaxy()
        existing_destinations = {route.destination_system_id for route in civilization.trade.routes}
        new_routes: list[TradeRoute] = []
        for system_id in civilization.controlled_system_ids:
            system = universe.find_system(system_id)
            for neighbor in galaxy.neighbors(system):
                if neighbor.id in existing_destinations or neighbor.id in civilization.controlled_system_ids:
                    continue
                if not neighbor.is_controlled():
                    continue
                route = TradeRoute(
                    id=TradeRouteId(id_sequence.next()),
                    civilization_id=civilization.id,
                    source_system_id=system.id,
                    destination_system_id=neighbor.id,
                    traffic=0.0,
                    capacity=neighbor.resource_summary.total_value() * 0.1,
                    value=neighbor.resource_summary.total_value() * 0.05,
                    active=True,
                )
                civilization.trade.routes.append(route)
                new_routes.append(route)
                existing_destinations.add(neighbor.id)
        return new_routes
