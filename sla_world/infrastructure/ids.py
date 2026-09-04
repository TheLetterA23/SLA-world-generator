from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SystemId:
    value: int


@dataclass(frozen=True, slots=True)
class StellarObjectId:
    value: int


@dataclass(frozen=True, slots=True)
class ConnectionId:
    value: int


@dataclass(frozen=True, slots=True)
class CivilizationId:
    value: int


@dataclass(frozen=True, slots=True)
class TradeRouteId:
    value: int


@dataclass(frozen=True, slots=True)
class WarId:
    value: int


class IdSequence:
    def __init__(self, start: int = 1) -> None:
        self._next_value = start

    def next(self) -> int:
        value = self._next_value
        self._next_value += 1
        return value
