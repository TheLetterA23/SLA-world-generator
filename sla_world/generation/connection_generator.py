from __future__ import annotations

from typing import Protocol

from sla_world.infrastructure.ids import IdSequence, ConnectionId, SystemId
from sla_world.infrastructure.random import RandomSource
from sla_world.domain.galaxy import Galaxy
from sla_world.domain.system import StarSystem
from sla_world.domain.connection import Connection
from sla_world.config.generation import ConnectionConfig


class ConnectionStrategy(Protocol):
    def propose_pairs(
        self, galaxy: Galaxy, config: ConnectionConfig, rng: RandomSource
    ) -> list[tuple[StarSystem, StarSystem]]: ...

class ConnectedDensityConnectionStrategy:
    def propose_pairs(
        self,
        galaxy: Galaxy,
        config: ConnectionConfig,
        rng: RandomSource,
    ) -> list[tuple[StarSystem, StarSystem]]:
        systems = galaxy.all_systems()

        if len(systems) < 2:
            return []

        pairs = self._propose_tree(galaxy, systems, config)
        tree_pairs = {
            self._pair_key(system, other)
            for system, other in pairs
        }

        pairs.extend(
            self._propose_shortcuts(
                galaxy,
                systems,
                config,
                rng,
                tree_pairs,
            )
        )

        return pairs

    def _propose_tree(
        self,
        galaxy: Galaxy,
        systems: list[StarSystem],
        config: ConnectionConfig,
    ) -> list[tuple[StarSystem, StarSystem]]:
        """
        Build a minimum spanning tree over the star systems.

        The tree guarantees that every system is reachable from every
        other system. Connections within max_distance are preferred,
        but if max_distance would make the galaxy disconnected, the
        shortest available connection is used instead.
        """
        connected: set[SystemId] = {systems[0].id}
        unconnected: set[SystemId] = {
            system.id for system in systems[1:]
        }

        pairs: list[tuple[StarSystem, StarSystem]] = []

        while unconnected:
            best_pair: tuple[StarSystem, StarSystem] | None = None
            best_distance = float("inf")
            best_within_range = False

            for system in systems:
                if system.id not in connected:
                    continue

                for other in systems:
                    if other.id not in unconnected:
                        continue

                    distance = galaxy.distance(system, other)
                    within_range = distance <= config.max_distance

                    # Prefer connections within max_distance.
                    # Among connections with the same range status,
                    # choose the shortest one.
                    if within_range and not best_within_range:
                        best_pair = (system, other)
                        best_distance = distance
                        best_within_range = True
                    elif within_range == best_within_range and distance < best_distance:
                        best_pair = (system, other)
                        best_distance = distance

            if best_pair is None:
                break

            system, other = best_pair

            pairs.append((system, other))
            connected.add(other.id)
            unconnected.remove(other.id)

        return pairs

    def _propose_shortcuts(
        self,
        galaxy: Galaxy,
        systems: list[StarSystem],
        config: ConnectionConfig,
        rng: RandomSource,
        existing_pairs: set[tuple[SystemId, SystemId]],
    ) -> list[tuple[StarSystem, StarSystem]]:
        """
        Add random connections between systems.

        These connections are not required for connectivity; they create
        alternate routes and loops in the galaxy.
        """
        pairs: list[tuple[StarSystem, StarSystem]] = []

        for index, system in enumerate(systems):
            for other in systems[index + 1:]:
                pair_key = self._pair_key(system, other)

                if pair_key in existing_pairs:
                    continue

                if galaxy.distance(system, other) > config.max_distance:
                    continue

                if rng.random() <= config.density:
                    pairs.append((system, other))
                    existing_pairs.add(pair_key)

        return pairs

    def _pair_key(
        self,
        system: StarSystem,
        other: StarSystem,
    ) -> frozenset[SystemId, SystemId]:
        return frozenset((system.id, other.id))

class DensityBasedConnectionStrategy:
    def propose_pairs(
        self, galaxy: Galaxy, config: ConnectionConfig, rng: RandomSource
    ) -> list[tuple[StarSystem, StarSystem]]:
        systems = galaxy.all_systems()
        pairs: list[tuple[StarSystem, StarSystem]] = []
        for index, system in enumerate(systems):
            for other in systems[index + 1:]:
                if galaxy.distance(system, other) > config.max_distance:
                    continue
                if rng.random() <= config.density:
                    pairs.append((system, other))
        return pairs


class ConnectionGenerator:
    def __init__(self, strategy: ConnectionStrategy | None = None) -> None:
        self._strategy = strategy or ConnectedDensityConnectionStrategy()

    def generate(
        self, galaxy: Galaxy, config: ConnectionConfig, id_sequence: IdSequence, rng: RandomSource
    ) -> list[Connection]:
        created: list[Connection] = []
        for system, other in self._strategy.propose_pairs(galaxy, config, rng):
            created.append(self._connect(galaxy, system, other, id_sequence))
        self._ensure_minimum_connections(galaxy, config, id_sequence)
        return created

    def _connect(self, galaxy: Galaxy, system: StarSystem, other: StarSystem, id_sequence: IdSequence) -> Connection:
        distance = galaxy.distance(system, other)
        connection = Connection(
            id=ConnectionId(id_sequence.next()),
            a=system.id,
            b=other.id,
            distance=distance,
            travel_cost=distance,
        )
        galaxy.add_connection(connection)
        return connection

    def _ensure_minimum_connections(self, galaxy: Galaxy, config: ConnectionConfig, id_sequence: IdSequence) -> None:
        for system in galaxy.all_systems():
            connected_ids = {galaxy.connections[cid].other(system.id) for cid in system.connection_ids}
            while len(system.connection_ids) < config.minimum_connections:
                candidates = [
                    other for other in galaxy.all_systems()
                    if other.id != system.id and other.id not in connected_ids
                ]
                if not candidates:
                    break
                target = min(candidates, key=lambda candidate: galaxy.distance(system, candidate))
                self._connect(galaxy, system, target, id_sequence)
                connected_ids.add(target.id)
