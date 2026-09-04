from __future__ import annotations

from sla_world.simulation.context import StellarTickContext
from sla_world.infrastructure.ids import IdSequence, WarId, CivilizationId
from sla_world.domain.civilization import Civilization, DiplomaticStance, SimulationEvent
from sla_world.domain.universe import Universe
from sla_world.domain.war import War
from sla_world.rules.diplomacy import (
    WarDeclarationPolicy,
    PeacePolicy,
    AlliancePolicy,
    SpreadingPowerWarPolicy,
    ExhaustionPeacePolicy,
    SimilarDevelopmentAlliancePolicy,
)


class DiplomacyHandler:
    def __init__(
        self,
        id_sequence: IdSequence,
        war_declaration_policy: WarDeclarationPolicy | None = None,
        peace_policy: PeacePolicy | None = None,
        alliance_policy: AlliancePolicy | None = None,
    ) -> None:
        self._id_sequence = id_sequence
        self._war_declaration_policy = war_declaration_policy or SpreadingPowerWarPolicy()
        self._peace_policy = peace_policy or ExhaustionPeacePolicy()
        self._alliance_policy = alliance_policy or SimilarDevelopmentAlliancePolicy()

    def execute(self, context: StellarTickContext) -> None:
        self._resolve_peace(context)
        self._declare_wars(context)
        self._form_alliances(context)

    def _bordering_civilizations(self, civilization: Civilization, universe: Universe) -> set[CivilizationId]:
        galaxy = universe.galaxy()
        borders: set[CivilizationId] = set()
        for system_id in civilization.controlled_system_ids:
            for neighbor in galaxy.neighbors(universe.find_system(system_id)):
                if neighbor.controlled_by is not None and neighbor.controlled_by != civilization.id:
                    borders.add(neighbor.controlled_by)
        return borders

    def _declare_wars(self, context: StellarTickContext) -> None:
        for civilization in context.universe.civilizations:
            for border_id in self._bordering_civilizations(civilization, context.universe):
                other = context.universe.civilization(border_id)
                if civilization.diplomacy.stance_with(other.id) is not DiplomaticStance.NEUTRAL:
                    continue
                if not self._war_declaration_policy.should_declare_war(civilization, other, context.universe):
                    continue
                self._start_war(civilization, other, context)

    def _start_war(self, attacker: Civilization, defender: Civilization, context: StellarTickContext) -> None:
        war = War(
            id=WarId(self._id_sequence.next()),
            attacker_id=attacker.id,
            defender_id=defender.id,
            started_at=context.clock.current_time,
        )
        context.universe.wars[war.id] = war
        attacker.active_war_ids.add(war.id)
        defender.active_war_ids.add(war.id)
        attacker.diplomacy.set_stance(defender.id, DiplomaticStance.WAR)
        defender.diplomacy.set_stance(attacker.id, DiplomaticStance.WAR)
        attacker.history.record(
            SimulationEvent(
                time=context.clock.current_time,
                kind="WarDeclared",
                actor_id=str(attacker.id.value),
                data={"defender_id": defender.id.value, "war_id": war.id.value},
            )
        )

    def _resolve_peace(self, context: StellarTickContext) -> None:
        for war in list(context.universe.wars.values()):
            if not war.active:
                continue
            attacker = context.universe.civilization(war.attacker_id)
            defender = context.universe.civilization(war.defender_id)
            attacker_wants_peace = self._peace_policy.should_seek_peace(attacker, war, context.universe)
            defender_wants_peace = self._peace_policy.should_seek_peace(defender, war, context.universe)
            if not (attacker_wants_peace or defender_wants_peace):
                continue
            self._end_war(war, attacker, defender, context)

    def _end_war(self, war: War, attacker: Civilization, defender: Civilization, context: StellarTickContext) -> None:
        war.active = False
        attacker.active_war_ids.discard(war.id)
        defender.active_war_ids.discard(war.id)
        attacker.diplomacy.set_stance(defender.id, DiplomaticStance.NEUTRAL)
        defender.diplomacy.set_stance(attacker.id, DiplomaticStance.NEUTRAL)
        for civilization, opponent in ((attacker, defender), (defender, attacker)):
            civilization.history.record(
                SimulationEvent(
                    time=context.clock.current_time,
                    kind="PeaceTreatySigned",
                    actor_id=str(civilization.id.value),
                    data={"opponent_id": opponent.id.value, "war_id": war.id.value},
                )
            )

    def _form_alliances(self, context: StellarTickContext) -> None:
        for civilization in context.universe.civilizations:
            for border_id in self._bordering_civilizations(civilization, context.universe):
                other = context.universe.civilization(border_id)
                if civilization.diplomacy.stance_with(other.id) is not DiplomaticStance.NEUTRAL:
                    continue
                if not self._alliance_policy.should_propose_alliance(civilization, other, context.universe):
                    continue
                if not self._alliance_policy.should_propose_alliance(other, civilization, context.universe):
                    continue
                self._form_alliance(civilization, other, context)

    def _form_alliance(self, first: Civilization, second: Civilization, context: StellarTickContext) -> None:
        first.diplomacy.set_stance(second.id, DiplomaticStance.ALLIANCE)
        second.diplomacy.set_stance(first.id, DiplomaticStance.ALLIANCE)
        for civilization, ally in ((first, second), (second, first)):
            civilization.history.record(
                SimulationEvent(
                    time=context.clock.current_time,
                    kind="AllianceFormed",
                    actor_id=str(civilization.id.value),
                    data={"ally_id": ally.id.value},
                )
            )
