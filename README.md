# SLA World Generation System

A Python implementation of the SLA world-generation design document, covering the "recommended
first implementation milestone" (design doc, section 49): domain model, deterministic generation,
a two-scale (stellar/interstellar) simulation engine, replaceable rules/policies, and on-demand
procedural detail generation.

## Quick start

```python
from sla_world import WorldBuilder, SimulationConfig

world = WorldBuilder.default().with_seed(42).build()

simulation = world.simulation(SimulationConfig.standard())
simulation.run(until=10_000)

for civilization in world.civilizations():
    print(
        civilization.name,
        world.spreading_power(civilization),
        len(world.controlled_systems(civilization)),
    )

system = world.systems()[0]
print(system.resource_summary.total_value())

for planet in system.planets():
    print(planet.name, planet.habitability.base_score, planet.control)

details = world.details.for_planet(system.habitable_planets()[0])
print(details.cities)
```

See `demo.py` for a complete runnable example.

## Layers

- **domain/** — persistent, dependency-free entities: `Universe`, `Galaxy`, `StarSystem`,
  `StellarObject` and its subclasses (`Star`, `Planet`, `Moon`, `AsteroidBelt`, `Nebula`,
  `BlackHole`), `Connection`, `Civilization`, `ResourceInventory`, `TradeRoute`. These objects
  hold state and relationships only; they contain no generation or simulation policy.
- **config/** — immutable configuration dataclasses for generation and simulation.
- **generation/** — `WorldBuilder` and the independent generators it composes
  (`StarMapGenerator`, `SystemGenerator`, `ConnectionGenerator`, `CivilizationSeeder`).
- **rules/** — replaceable policies consumed by the simulation and application layers:
  `HabitabilityEvaluator`, `SpreadingRateCalculator`, `ColonizationTargetSelector`,
  `TradeRoutePolicy`, and `UniverseValidator` for invariant checks.
- **simulation/** — `SimulationEngine` driving stellar and interstellar ticks through small,
  composable handlers (`ResourceUtilizationHandler`, `PlanetaryDevelopmentHandler`,
  `LocalColonizationHandler`, `ExplorationHandler`, `ExpansionHandler`, `TradeRouteHandler`)
  rather than one large method.
- **procedural/** — on-demand, ephemeral detail derived from persistent state:
  `CityGenerator`, `PlanetDetailGenerator`, `TrafficEstimator`. Nothing here is stored back
  onto the domain objects.
- **infrastructure/** — `RandomSource`/`SeededRandom`/`RandomStreams` (deterministic, named
  random streams so unrelated systems can't perturb each other's outcomes) and `IdSequence`.
- **application.py** — the `World` facade (what `WorldBuilder.build()` returns) and
  `DetailServices`. This is the layer the design document calls "Application Layer:
  WorldBuilder / SimulationRunner / Queries" — it wires the domain graph together with rules
  and services without those dependencies leaking into the domain objects themselves.

## Notable design decisions vs. the source document

- **Ownership**: `StarSystem`/`Civilization` hold IDs only (`controlled_system_ids`,
  `controlled_planet_ids`, `connection_ids`), never embedded copies of other aggregates,
  per the document's aggregate-boundary guidance (section 36). `Universe` and `Galaxy` are the
  indexes that resolve IDs back into objects.
- **Stellar object identity**: rather than a separate `PlanetId`/`MoonId` type that narrows
  `StellarObject.id` in a way that breaks static type-checking on subclassing, every
  `StellarObject` (including `Planet` and `Moon`) shares one `StellarObjectId` type. `SystemId`,
  `ConnectionId`, `CivilizationId`, and `TradeRouteId` remain distinct, since those are never
  used interchangeably with a stellar object's identity.
- **Query API**: rather than putting graph-traversal methods (`civilization.systems()`,
  `civilization.spreading_power()`) directly on the `Civilization` dataclass — which would force
  domain entities to hold back-references to the whole universe — those conveniences live on the
  `World` facade (`world.controlled_systems(civilization)`, `world.spreading_power(civilization)`).
  This keeps the domain layer free of simulation/query dependencies, per the document's own
  layering rule in section 2.
- **Determinism**: `RandomStreams` derives a per-name seed via SHA-256 of `f"{seed}:{name}"`
  rather than Python's built-in `hash()`, so streams are reproducible across processes
  (`hash()` on strings is randomized per-process unless `PYTHONHASHSEED` is fixed).

## Scope

This targets the document's section 49 milestone (items 1–15) plus a light traffic estimator,
since the purpose section explicitly calls for systems deriving traffic on demand. Ships,
diplomacy mechanics, and technology trees are intentionally left out, per section 48's
"avoid over-modeling in version 1" guidance — `DiplomacyState` exists as a minimal, extensible
placeholder but no diplomacy policy acts on it yet. Connection generation is O(n²) in star
count, which is fine at the demo's scale (hundreds of systems) but would want the spatial
indexing extension point mentioned in section 37 for much larger maps.
