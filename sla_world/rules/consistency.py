from __future__ import annotations

from dataclasses import dataclass, field

from sla_world.domain.universe import Universe


@dataclass
class ValidationReport:
    issues: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.issues

    def add(self, issue: str) -> None:
        self.issues.append(issue)


class UniverseValidator:
    def validate(self, universe: Universe) -> ValidationReport:
        report = ValidationReport()
        system_ids = {system.id for system in universe.systems()}
        planet_ids = {planet.id for planet in universe.planets()}
        self._validate_civilizations(universe, system_ids, planet_ids, report)
        self._validate_connections(universe, report)
        return report

    def _validate_civilizations(self, universe: Universe, system_ids, planet_ids, report: ValidationReport) -> None:
        for civilization in universe.civilizations:
            if civilization.origin_world_id not in planet_ids:
                report.add(f"Civilization {civilization.name} has a missing origin world")
            for system_id in civilization.controlled_system_ids:
                if system_id not in system_ids:
                    report.add(f"Civilization {civilization.name} controls a missing system {system_id}")
            for planet_id in civilization.controlled_planet_ids:
                if planet_id not in planet_ids:
                    report.add(f"Civilization {civilization.name} controls a missing planet {planet_id}")

    def _validate_connections(self, universe: Universe, report: ValidationReport) -> None:
        for galaxy in universe.galaxies:
            for connection in galaxy.connections.values():
                if connection.a not in galaxy.systems or connection.b not in galaxy.systems:
                    report.add(f"Connection {connection.id} references a missing system")
