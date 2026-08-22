from __future__ import annotations

from dataclasses import dataclass, field

from sla_world.infrastructure.ids import TradeRouteId, CivilizationId, SystemId


@dataclass
class TradeRoute:
    id: TradeRouteId
    civilization_id: CivilizationId
    source_system_id: SystemId
    destination_system_id: SystemId
    traffic: float
    capacity: float
    value: float
    active: bool = True


@dataclass
class TradeState:
    routes: list[TradeRoute] = field(default_factory=list)

    def active_routes(self) -> list[TradeRoute]:
        return [route for route in self.routes if route.active]

    def total_trade_value(self) -> float:
        return sum(route.value for route in self.active_routes())
