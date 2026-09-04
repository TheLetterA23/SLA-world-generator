from __future__ import annotations

from sla_world.simulation.context import StellarTickContext
from sla_world.domain.civilization import Civilization, SimulationEvent
from sla_world.domain.system import StarSystem
from sla_world.domain.universe import Universe
from sla_world.domain.war import War
from sla_world.infrastructure.ids import SystemId


class WarHandler:
    def __init__(self, capture_chance: float = 0.01, exhaustion_per_tick: float = 0.002) -> None:
        self._capture_chance = capture_chance
        self._exhaustion_per_tick = exhaustion_per_tick

    def execute(self, context: StellarTickContext) -> None:
        for war in list(context.universe.wars.values()):
            if not war.active:
                continue
            war.add_exhaustion(war.attacker_id, self._exhaustion_per_tick)
            war.add_exhaustion(war.defender_id, self._exhaustion_per_tick)
            self._attempt_captures(war, context)

    def _attempt_captures(self, war: War, context: StellarTickContext) -> None:
        attacker = context.universe.civilization(war.attacker_id)
        defender = context.universe.civilization(war.defender_id)
        for owner, enemy in ((attacker, defender), (defender, attacker)):
            frontier = self._enemy_frontier_systems(owner, enemy, context.universe)
            if not frontier or context.rng.random() > self._capture_chance:
                continue
            self._capture(context.rng.choice(frontier), owner, enemy, context)

    def _enemy_frontier_systems(self, owner: Civilization, enemy: Civilization, universe: Universe) -> list[StarSystem]:
        galaxy = universe.galaxy()
        frontier: dict[SystemId, StarSystem] = {}
        for system_id in owner.controlled_system_ids:
            for neighbor in galaxy.neighbors(universe.find_system(system_id)):
                if neighbor.controlled_by == enemy.id:
                    frontier[neighbor.id] = neighbor
        return list(frontier.values())

    def _capture(self, system: StarSystem, owner: Civilization, enemy: Civilization, context: StellarTickContext) -> None:
        enemy.controlled_system_ids.discard(system.id)
        owner.controlled_system_ids.add(system.id)
        system.controlled_by = owner.id
        owner.history.record(
            SimulationEvent(
                time=context.clock.current_time,
                kind="SystemCaptured",
                actor_id=str(owner.id.value),
                data={"system_id": system.id.value, "from_civilization_id": enemy.id.value},
            )
        )
