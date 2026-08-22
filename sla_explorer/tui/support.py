from __future__ import annotations

from typing import cast

from textual.screen import Screen
from textual.widgets.data_table import RowKey

from sla_explorer.context import SimulationContext


def context_of(screen: Screen) -> SimulationContext:
    return cast(SimulationContext, getattr(screen.app, "context"))


def row_key_int(row_key: RowKey) -> int:
    value = row_key.value
    assert value is not None
    return int(value)
