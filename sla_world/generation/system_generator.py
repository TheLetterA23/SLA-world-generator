from __future__ import annotations

from sla_world.infrastructure.ids import IdSequence, StellarObjectId
from sla_world.infrastructure.random import RandomSource
from sla_world.domain.system import StarSystem
from sla_world.domain.stellar_objects import Star, Moon, AsteroidBelt
from sla_world.domain.planet import Planet, PlanetType, Atmosphere, HabitabilityProfile
from sla_world.domain.resources import ResourceType, ResourceInventory
from sla_world.config.generation import SystemGenerationConfig

_ALL_RESOURCE_TYPES = list(ResourceType)
_HABITABLE_PLANET_TYPES = (PlanetType.ROCKY, PlanetType.OCEAN)


def _random_resources(rng: RandomSource, richness: float, resource_count: int) -> ResourceInventory:
    inventory = ResourceInventory.empty()
    for resource in rng.sample(_ALL_RESOURCE_TYPES, resource_count):
        inventory = inventory.add(resource, rng.uniform(10.0, 500.0) * richness)
    return inventory


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def _random_habitability(rng: RandomSource, planet_type: PlanetType) -> HabitabilityProfile:
    baseline = 0.6 if planet_type in _HABITABLE_PLANET_TYPES else 0.15
    spread = 0.4
    return HabitabilityProfile(
        temperature_score=_clamp_unit(baseline + rng.uniform(-spread, spread)),
        atmosphere_score=_clamp_unit(baseline + rng.uniform(-spread, spread)),
        water_score=_clamp_unit(baseline + rng.uniform(-spread, spread)),
        biosphere_score=_clamp_unit(baseline + rng.uniform(-spread, spread)),
    )


def _random_atmosphere(rng: RandomSource, planet_type: PlanetType) -> Atmosphere:
    breathable = planet_type in _HABITABLE_PLANET_TYPES and rng.random() > 0.5
    return Atmosphere(
        density=rng.uniform(0.0, 2.0),
        breathable=breathable,
        composition="nitrogen-oxygen" if breathable else "unbreathable",
    )


def _planet_label(index: int) -> str:
    return chr(ord("a") + index - 1) if index <= 26 else str(index)


class ResourceAggregation:
    @staticmethod
    def update_system(system: StarSystem) -> None:
        inventory = ResourceInventory.empty()
        for star in system.stars:
            inventory = inventory.merge(star.resources)
        for stellar_object in system.objects:
            inventory = inventory.merge(stellar_object.resources)
        system.resource_summary = inventory


class SystemGenerator:
    def __init__(self, config: SystemGenerationConfig) -> None:
        self._config = config

    def generate(self, system: StarSystem, id_sequence: IdSequence, rng: RandomSource) -> None:
        self._generate_star(system, id_sequence, rng)
        planet_count = rng.randint(self._config.min_planets, self._config.max_planets)
        for _ in range(planet_count):
            self._generate_planet(system, id_sequence, rng)
        if rng.random() < self._config.asteroid_belt_chance:
            self._generate_asteroid_belt(system, id_sequence, rng)
        ResourceAggregation.update_system(system)

    def _generate_star(self, system: StarSystem, id_sequence: IdSequence, rng: RandomSource) -> None:
        star = Star(
            id=StellarObjectId(id_sequence.next()),
            name=f"{system.name} Prime",
            mass=rng.uniform(0.3, 3.0),
            radius=rng.uniform(0.5, 2.5),
            spectral_class=rng.choice(["O", "B", "A", "F", "G", "K", "M"]),
            luminosity=rng.uniform(0.1, 5.0),
        )
        system.stars.append(star)

    def _generate_planet(self, system: StarSystem, id_sequence: IdSequence, rng: RandomSource) -> None:
        planet_type = rng.choice(list(PlanetType))
        planet = Planet(
            id=StellarObjectId(id_sequence.next()),
            name=f"{system.name} {_planet_label(len(system.planets()) + 1)}",
            mass=rng.uniform(0.1, 15.0),
            radius=rng.uniform(0.3, 4.0),
            resources=_random_resources(rng, self._config.resource_richness, rng.randint(1, 4)),
            planet_type=planet_type,
            atmosphere=_random_atmosphere(rng, planet_type),
            habitability=_random_habitability(rng, planet_type),
            parent_system_id=system.id,
        )
        moon_count = rng.randint(self._config.min_moons_per_planet, self._config.max_moons_per_planet)
        for _ in range(moon_count):
            moon = self._generate_moon(planet, id_sequence, rng)
            system.objects.append(moon)
            planet.moon_ids.append(moon.id)
        system.objects.append(planet)

    def _generate_moon(self, planet: Planet, id_sequence: IdSequence, rng: RandomSource) -> Moon:
        return Moon(
            id=StellarObjectId(id_sequence.next()),
            name=f"{planet.name} Moon {rng.randint(1, 999)}",
            mass=rng.uniform(0.001, 0.5),
            radius=rng.uniform(0.05, 0.6),
            resources=_random_resources(rng, self._config.resource_richness, rng.randint(0, 2)),
            parent_planet_id=planet.id,
        )

    def _generate_asteroid_belt(self, system: StarSystem, id_sequence: IdSequence, rng: RandomSource) -> None:
        belt = AsteroidBelt(
            id=StellarObjectId(id_sequence.next()),
            name=f"{system.name} Belt",
            mass=rng.uniform(0.01, 0.2),
            radius=None,
            resources=_random_resources(rng, self._config.resource_richness, rng.randint(1, 3)),
            density=rng.uniform(0.1, 1.0),
        )
        system.objects.append(belt)
