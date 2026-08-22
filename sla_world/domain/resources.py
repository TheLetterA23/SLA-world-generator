from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Mapping


class ResourceType(Enum):
    IRON = auto()
    WATER = auto()
    HYDROGEN = auto()
    RARE_METALS = auto()
    ORGANICS = auto()
    ENERGY_CRYSTALS = auto()
    SILICATES = auto()
    TITANIUM = auto()


_RESOURCE_BASE_VALUE: Mapping[ResourceType, float] = {
    ResourceType.IRON: 1.0,
    ResourceType.WATER: 1.5,
    ResourceType.HYDROGEN: 1.0,
    ResourceType.RARE_METALS: 4.0,
    ResourceType.ORGANICS: 2.0,
    ResourceType.ENERGY_CRYSTALS: 6.0,
    ResourceType.SILICATES: 1.2,
    ResourceType.TITANIUM: 3.5,
}


@dataclass(frozen=True, slots=True)
class ResourceAmount:
    resource: ResourceType
    quantity: float


@dataclass(frozen=True)
class ResourceInventory:
    amounts: Mapping[ResourceType, float] = field(default_factory=dict)

    def amount(self, resource: ResourceType) -> float:
        return self.amounts.get(resource, 0.0)

    def total_value(self) -> float:
        return sum(quantity * _RESOURCE_BASE_VALUE[resource] for resource, quantity in self.amounts.items())

    def add(self, resource: ResourceType, quantity: float) -> "ResourceInventory":
        updated = dict(self.amounts)
        updated[resource] = updated.get(resource, 0.0) + quantity
        return ResourceInventory(updated)

    def remove(self, resource: ResourceType, quantity: float) -> "ResourceInventory":
        updated = dict(self.amounts)
        remaining = updated.get(resource, 0.0) - quantity
        updated[resource] = max(remaining, 0.0)
        return ResourceInventory(updated)

    def merge(self, other: "ResourceInventory") -> "ResourceInventory":
        updated = dict(self.amounts)
        for resource, quantity in other.amounts.items():
            updated[resource] = updated.get(resource, 0.0) + quantity
        return ResourceInventory(updated)

    @staticmethod
    def empty() -> "ResourceInventory":
        return ResourceInventory({})
