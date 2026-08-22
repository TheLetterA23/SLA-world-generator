# Developer Guide

This guide is for anyone extending or integrating with the `sla_world` package: where things
live, what each module is responsible for, exactly what fields every object carries, and how to
plug in your own logic without touching the core. For the high-level design rationale, see
`README.md`.

## Contents

- [Setup](#setup)
- [How a world comes together](#how-a-world-comes-together)
- [Project structure](#project-structure)
- [Layer-by-layer reference](#layer-by-layer-reference)
  - [`infrastructure/`](#infrastructure)
  - [`domain/`](#domain)
  - [`config/`](#config)
  - [`generation/`](#generation)
  - [`rules/`](#rules)
  - [`simulation/`](#simulation)
  - [`procedural/`](#procedural)
  - [`application.py`](#applicationpy)
- [Object structures](#object-structures)
  - [Identifiers](#identifiers)
  - [Shared value types](#shared-value-types)
  - [Resources](#resources)
  - [Stellar objects](#stellar-objects)
  - [Planets and ownership](#planets-and-ownership)
  - [Connections](#connections)
  - [Star systems](#star-systems)
  - [Galaxy and Universe](#galaxy-and-universe)
  - [Civilizations](#civilizations)
  - [Configuration objects](#configuration-objects)
  - [Simulation runtime objects](#simulation-runtime-objects)
  - [Procedural output objects](#procedural-output-objects)
- [Where information lives](#where-information-lives)
- [Common recipes](#common-recipes)
  - [Generate a world](#generate-a-world)
  - [Run a simulation](#run-a-simulation)
  - [Read planet and system state](#read-planet-and-system-state)
  - [Generate on-demand detail](#generate-on-demand-detail)
  - [Swap in your own rule](#swap-in-your-own-rule)
  - [Add a new simulation handler](#add-a-new-simulation-handler)
  - [Add a new stellar object type](#add-a-new-stellar-object-type)
  - [Validate universe invariants](#validate-universe-invariants)
- [Conventions](#conventions)
- [Testing and type-checking](#testing-and-type-checking)

## Setup

The package has no third-party runtime dependencies — only the standard library. From the
project root:

```bash
python3 -m mypy sla_world --ignore-missing-imports
python3 demo.py
```

`demo.py` is a complete, runnable example: it builds a galaxy, runs a simulation, and prints
civilization, planet, and traffic data.

## How a world comes together

There are three distinct phases, and understanding them is the key to understanding the whole
package:

1. **Generation** (`generation/`) runs once. `WorldBuilder` composes four independent
   generators to produce a `Universe`: a star map, then per-system contents, then connections
   between systems, then civilizations seeded onto habitable worlds. It returns a `World`.
2. **Simulation** (`simulation/`) runs repeatedly. `World.simulation(config)` builds a
   `SimulationRun`, which advances a clock and, on each tick, hands a small context object to a
   list of handlers — colonization, resource extraction, expansion, trade, and so on. Handlers
   mutate the `Universe` in place.
3. **Procedural detail** (`procedural/`) runs on demand, whenever you ask for it, and is never
   stored back onto the domain objects. `World.details.for_planet(planet)` derives a
   `PlanetDetails` (cities, population) from a planet's current state; ask again later and
   you'll get an answer reflecting the planet's current development.

Everything is deterministic given a seed: the same `WorldBuilder(...).with_seed(42).build()`
followed by the same sequence of `simulation.run(...)` calls always produces the same universe.

## Project structure

```
sla_world/
  __init__.py                      Public API re-exports
  application.py                   World facade + DetailServices
  demo.py                          Runnable end-to-end example
  domain/                          Persistent state, no policy logic
    values.py                        Position, SimulationTime, Duration
    resources.py                     ResourceType, ResourceInventory
    stellar_objects.py               StellarObject, Star, Moon, AsteroidBelt, Nebula, BlackHole
    planet.py                        Planet, PlanetType, Atmosphere, HabitabilityProfile, Control
    connection.py                    Connection
    system.py                        StarSystem
    galaxy.py                        Galaxy
    development.py                   CivilizationDevelopment
    trade.py                         TradeRoute, TradeState
    civilization.py                  Civilization, DiplomacyState, CivilizationHistory
    universe.py                      Universe (top-level aggregate + indexes)
  config/                           Immutable configuration dataclasses
    generation.py                    StarMapConfig, SystemGenerationConfig, ConnectionConfig,
                                      CivilizationSeedConfig, WorldGenerationConfig
    simulation.py                    SimulationConfig
  generation/                      Runs once, builds a Universe
    star_map_generator.py            StarMapGenerator, SpatialDistribution
    system_generator.py              SystemGenerator, ResourceAggregation
    connection_generator.py          ConnectionGenerator, ConnectionStrategy
    civilization_seeder.py           CivilizationSeeder, CivilizationSeedStrategy
    world_builder.py                 WorldBuilder (the entry point)
  rules/                           Replaceable policies, all Protocol-based
    habitability.py                  HabitabilityEvaluator
    spreading.py                     SpreadingRateCalculator
    colonization.py                  ColonizationTargetSelector
    trade.py                         TradeRoutePolicy
    consistency.py                   UniverseValidator, ValidationReport
  simulation/                      Runs repeatedly, mutates a Universe
    clock.py                         SimulationClock
    context.py                       StellarTickContext, InterstellarTickContext
    ticks.py                         StellarTickHandler, InterstellarTickHandler (Protocols)
    engine.py                        SimulationEngine, SimulationRun
    systems/                         Stellar-tick handlers (fine-grained, per-system)
      resource_utilization.py          ResourceUtilizationHandler
      development.py                   PlanetaryDevelopmentHandler
      colonization.py                  LocalColonizationHandler
      exploration.py                   ExplorationHandler
    interstellar/                    Interstellar-tick handlers (coarse-grained, galaxy-wide)
      expansion.py                     ExpansionHandler
      trading.py                       TradeRouteHandler
  procedural/                      On-demand, ephemeral detail generation
    cities.py                        City, CityGenerator
    planet_details.py                PlanetDetails, PlanetDetailGenerator, DetailLevel
    traffic.py                       TrafficProfile, TrafficEstimator
  infrastructure/                  Cross-cutting technical concerns
    ids.py                           SystemId, StellarObjectId, ConnectionId, CivilizationId,
                                      TradeRouteId, IdSequence
    random.py                        RandomSource, SeededRandom, RandomStreams
```

## Layer-by-layer reference

### `infrastructure/`

**`ids.py`** — every entity ID is a small frozen dataclass wrapping an `int` (e.g. `SystemId`,
`CivilizationId`), so you can't accidentally pass a `SystemId` where a `CivilizationId` is
expected. `IdSequence` is a simple monotonically increasing counter shared across generation and
simulation so IDs never collide.

**`random.py`** — `RandomSource` is the `Protocol` every generator and handler depends on
(`random()`, `uniform()`, `choice()`, `randint()`, `sample()`), so you can substitute your own
implementation in tests. `SeededRandom` wraps `random.Random`. `RandomStreams` derives an
independent, reproducible `SeededRandom` per named stream from one root seed, using
`sha256(f"{seed}:{name}")` rather than Python's `hash()` — this matters because `hash()` on
strings is randomized per-process unless `PYTHONHASHSEED` is fixed, which would silently break
reproducibility.

```python
from sla_world.infrastructure.random import RandomStreams

streams = RandomStreams(root_seed=42)
star_rng = streams.stream("generation.star_map")
system_rng = streams.stream("generation.systems")
```

### `domain/`

Plain dataclasses with no dependency on generation, simulation, or config. This is the layer you
read when you want to know what data exists, not how it got there. Full field-by-field detail is
in [Object structures](#object-structures) below; the summary:

- `StellarObject` is the base for anything that can sit in a system: `Star`, `Planet`, `Moon`,
  `AsteroidBelt`, `Nebula`, `BlackHole`. All of them share one `StellarObjectId` type.
- `Planet.control: Control | None` is how ownership is modeled — `None` means unclaimed.
- `StarSystem` and `Civilization` store **IDs only** for cross-references
  (`connection_ids: set[ConnectionId]`, `controlled_system_ids: set[SystemId]`, etc.), never
  embedded copies of other aggregates. `Galaxy` and `Universe` are the indexes that resolve
  those IDs back into objects — see `Galaxy.neighbors()`, `Universe.find_system()`,
  `Universe.find_planet()`.
- `Universe` is the top-level aggregate: a list of `Galaxy` plus a list of `Civilization`, with
  private ID-keyed indexes rebuilt by `Universe.reindex()` (called automatically in
  `__post_init__`).

### `config/`

Frozen dataclasses only — no behavior. `WorldGenerationConfig.default()` and
`SimulationConfig.standard()` give you sane defaults; construct your own for anything else.

### `generation/`

Four independent generators, each consumed only by `WorldBuilder`:

| Generator | Input | Output |
|---|---|---|
| `StarMapGenerator` | `StarMapConfig` | a `Galaxy` populated with empty `StarSystem`s |
| `SystemGenerator` | `SystemGenerationConfig`, one `StarSystem` | fills that system with a star, planets, moons, an optional belt |
| `ConnectionGenerator` | `ConnectionConfig`, a `Galaxy` | `Connection`s between systems |
| `CivilizationSeeder` | `CivilizationSeedConfig`, a `Galaxy` | `Civilization`s, each with a colonized origin world |

Each one accepts an injectable strategy (`SpatialDistribution`, `ConnectionStrategy`,
`CivilizationSeedStrategy`) so you can change *how* something is chosen without touching the
generator's orchestration logic. `WorldBuilder.build()` runs them in that order and wraps the
resulting `Universe` in a `World`.

### `rules/`

Small, stateless(ish) policy objects, each behind a `Protocol` so they're swappable:

- `HabitabilityEvaluator.score(planet, civilization, universe)` — how good a target planet is
  for a given civilization, weighing the planet's raw habitability against similarity to that
  civilization's origin world.
- `SpreadingRateCalculator.calculate(civilization, universe)` — a civilization's expansion
  drive, from `ResourceBasedSpreadingRate` (development level combined with how much of its
  controlled resources it's actually using).
- `ColonizationTargetSelector.choose(civilization, system, universe)` — which unclaimed planet
  in a system (if any) a civilization colonizes next.
- `TradeRoutePolicy.update_routes(civilization, universe, id_sequence)` — which new
  `TradeRoute`s to open.
- `UniverseValidator.validate(universe)` — checks referential integrity (no civilization
  controlling a system/planet that doesn't exist, no connection pointing at a missing system)
  and returns a `ValidationReport`.

### `simulation/`

`SimulationEngine` holds two lists of handlers — `stellar_handlers` and
`interstellar_handlers` — each implementing the `StellarTickHandler` /
`InterstellarTickHandler` `Protocol` (just an `execute(context)` method).
`SimulationEngine.standard(id_sequence)` wires up the default set:

- Stellar (runs every tick): `ResourceUtilizationHandler` → `PlanetaryDevelopmentHandler` →
  `LocalColonizationHandler` → `ExplorationHandler`.
- Interstellar (runs every `interstellar_tick_length / stellar_tick_length` stellar ticks):
  `ExpansionHandler` → `TradeRouteHandler`.

`SimulationRun` (returned by `World.simulation(config)`) owns the `SimulationClock` and two
named `RandomStreams` (`"simulation.stellar"`, `"simulation.interstellar"`), and its `run(until)`
method drives the loop, optionally calling `UniverseValidator` after each tick if
`config.validate_after_tick` is set.

### `procedural/`

Nothing here is persisted. `PlanetDetailGenerator.generate(planet, civilization, detail_level)`
seeds a local `SeededRandom` from `planet.id.value`, so calling it twice for the same planet in
the same development state gives the same cities — but nothing is written back to `Planet`.
`TrafficEstimator.estimate(system, universe)` is a similarly cheap, stateless derivation.

### `application.py`

`World` is what `WorldBuilder.build()` returns, and is the intended entry point for consumers —
it wraps the raw `Universe` (accessible via `world.universe`) with:

- read helpers: `systems()`, `planets()`, `civilizations()`, `find_system()`, `find_planet()`,
  `civilization()`
- civilization-relative queries: `controlled_systems()`, `controlled_planets()`,
  `origin_world()`, `spreading_power()` — these live here rather than on `Civilization` itself
  so the domain layer never needs a back-reference to the whole universe
- `simulation(config)` to start a `SimulationRun`
- `details`, a `DetailServices` instance, for on-demand procedural generation

## Object structures

Every dataclass in the project, field by field. Types shown are exactly what's in the source;
`| None` fields default to `None` unless noted otherwise. Frozen dataclasses (immutable — methods
that "modify" them, like `ResourceInventory.add`, actually return a new instance) are marked
**frozen**.

### Identifiers

All in `infrastructure/ids.py`. Each is a **frozen** single-field wrapper around an `int`, so
`SystemId(3) == SystemId(3)` but `SystemId(3) != StellarObjectId(3)` — the type checker (and a
`set`/`dict` key) will never let you confuse a system with a stellar object just because their
underlying integers happen to match.

| Type | Wraps | Identifies |
|---|---|---|
| `SystemId` | `int` | a `StarSystem` |
| `StellarObjectId` | `int` | any `StellarObject` — stars, planets, moons, belts, nebulae, black holes all share this one type |
| `ConnectionId` | `int` | a `Connection` |
| `CivilizationId` | `int` | a `Civilization` |
| `TradeRouteId` | `int` | a `TradeRoute` |

`IdSequence(start=1)` is not an ID itself — it's a mutable counter (`.next()` returns an `int`
and increments). One `IdSequence` is created per `WorldBuilder.build()` call and threaded through
every generator and, later, every simulation handler that needs to mint new IDs (like
`TradeRouteHandler`), so IDs never collide between generation-time and simulation-time objects.

### Shared value types

In `domain/values.py`.

| Type | Definition | Notes |
|---|---|---|
| `SimulationTime` | `NewType("SimulationTime", int)` | in-universe time units elapsed; what `SimulationClock.current_time` counts in |
| `Duration` | `NewType("Duration", int)` | a span of `SimulationTime`, used for tick lengths |
| `Position` (**frozen**) | `x: float`, `y: float`, `z: float = 0.0` | plus `distance_to(other)` (Euclidean) |

### Resources

In `domain/resources.py`.

`ResourceType` is an `Enum` with eight members: `IRON`, `WATER`, `HYDROGEN`, `RARE_METALS`,
`ORGANICS`, `ENERGY_CRYSTALS`, `SILICATES`, `TITANIUM`. Each has a fixed per-unit base value used
only by `ResourceInventory.total_value()`:

| Resource | Base value |
|---|---|
| `IRON` | 1.0 |
| `WATER` | 1.5 |
| `HYDROGEN` | 1.0 |
| `RARE_METALS` | 4.0 |
| `ORGANICS` | 2.0 |
| `ENERGY_CRYSTALS` | 6.0 |
| `SILICATES` | 1.2 |
| `TITANIUM` | 3.5 |

`ResourceAmount` (**frozen**) is a simple pair: `resource: ResourceType`, `quantity: float`. It
isn't used internally (inventories store a plain mapping) but is available if you want a
lightweight value to pass around, e.g. as a handler's return value.

`ResourceInventory` (**frozen**) wraps one field, `amounts: Mapping[ResourceType, float]`
(defaults to `{}`), and is immutable — every mutating-looking method returns a new instance:

| Method | Returns | Behavior |
|---|---|---|
| `amount(resource)` | `float` | `0.0` if the resource isn't present |
| `total_value()` | `float` | sum of `quantity * base_value` across all held resources |
| `add(resource, quantity)` | `ResourceInventory` | new inventory with `quantity` added |
| `remove(resource, quantity)` | `ResourceInventory` | new inventory, floored at `0.0` |
| `merge(other)` | `ResourceInventory` | new inventory with both inventories' quantities summed |
| `ResourceInventory.empty()` | `ResourceInventory` | the canonical empty inventory (used as most dataclass defaults) |

### Stellar objects

In `domain/stellar_objects.py`. `StellarObject` is the base class for everything a `StarSystem`
can contain (except that `Star`s live in their own `system.stars` list — see
[Star systems](#star-systems)):

| Field | Type | Notes |
|---|---|---|
| `id` | `StellarObjectId` | required |
| `name` | `str` | required |
| `mass` | `float \| None` | required (pass `None` explicitly if unknown — e.g. `AsteroidBelt` generation does this for `radius`) |
| `radius` | `float \| None` | required |
| `resources` | `ResourceInventory` | defaults to `ResourceInventory.empty()` |

Plus `resource_value() -> float`, a thin wrapper over `resources.total_value()`.

Subclasses only add their own fields (all inherited fields keep their meaning above):

| Class | Extra fields |
|---|---|
| `Star` | `spectral_class: str = "G"`, `luminosity: float = 1.0` |
| `Moon` | `parent_planet_id: StellarObjectId \| None = None` |
| `AsteroidBelt` | `density: float = 1.0` |
| `Nebula` | `composition: str = "gas"` |
| `BlackHole` | `event_horizon_radius: float = 0.0` |

`Planet` is also a `StellarObject` subclass but is large enough to get its own section below.

### Planets and ownership

In `domain/planet.py`.

`PlanetType` is an `Enum`: `ROCKY`, `OCEAN`, `ICE`, `GAS_GIANT`, `DESERT`, `VOLCANIC`, `BARREN`.

`Atmosphere` (**frozen**): `density: float`, `breathable: bool`, `composition: str` — all
required, no defaults (a default *instance* is built by the private `_default_atmosphere()`
factory used as `Planet.atmosphere`'s field default).

`HabitabilityProfile` (**frozen**): four required `float` scores —
`temperature_score`, `atmosphere_score`, `water_score`, `biosphere_score` — plus a computed
`base_score` property (their average). This is the single number most habitability-related code
(`Planet.is_habitable()`, `HabitabilityEvaluator`, `CivilizationSeeder`) actually reads.

`PlanetDevelopment` — **not frozen**, this one is mutated in place by simulation handlers:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `population` | `float` | `0.0` | normalized 0–1 score, *not* a headcount |
| `infrastructure` | `float` | `0.0` | normalized 0–1 score |
| `industry` | `float` | `0.0` | normalized 0–1 score |
| `urbanization` | `float` | `0.0` | normalized 0–1 score; drives how many cities `CityGenerator` produces |

`Control` — exists only when a planet has an owner:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `civilization_id` | `CivilizationId` | required | who owns this planet |
| `established_at` | `SimulationTime` | required | when ownership began |
| `development` | `PlanetDevelopment` | new empty `PlanetDevelopment()` | this planet's own growth state |

`Planet` (subclasses `StellarObject`, so it also has `id`, `name`, `mass`, `radius`, `resources`
from the base class):

| Field | Type | Default | Meaning |
|---|---|---|---|
| `planet_type` | `PlanetType` | `PlanetType.ROCKY` | |
| `atmosphere` | `Atmosphere` | density `0.0`, not breathable, `"none"` | |
| `habitability` | `HabitabilityProfile` | all scores `0.0` | |
| `parent_system_id` | `SystemId \| None` | `None` | which `StarSystem` this planet belongs to |
| `moon_ids` | `list[StellarObjectId]` | `[]` | IDs of this planet's `Moon` objects, which live in `system.objects` alongside the planet |
| `control` | `Control \| None` | `None` | `None` means unclaimed |

Plus three read helpers: `is_habitable(threshold=0.5)`, `owner` (property, shortcut for
`control.civilization_id if control else None`), `development` (property, shortcut for
`control.development if control else None`), and `development_level` (property, the average of
the four `PlanetDevelopment` scores, or `0.0` if unclaimed).

### Connections

In `domain/connection.py`. `Connection` (**frozen**): `id: ConnectionId`, `a: SystemId`,
`b: SystemId`, `distance: float`, `travel_cost: float` — all required. `other(system_id)` returns
whichever of `a`/`b` isn't the one you passed (raises `ValueError` if the connection doesn't
touch that system at all); `connects(system_id)` is a boolean membership check.

`travel_cost` is currently always equal to `distance` (see `ConnectionGenerator._connect`), but
they're kept as separate fields so a future strategy can price routes differently — for example,
a connection strategy that penalizes crossing a hazardous nebula.

### Star systems

In `domain/system.py`. `StarSystem`:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `id` | `SystemId` | required | |
| `name` | `str` | required | |
| `position` | `Position` | required | |
| `stars` | `list[Star]` | `[]` | usually exactly one, from `SystemGenerator._generate_star` |
| `objects` | `list[StellarObject]` | `[]` | everything *except* stars: planets, moons, belts, nebulae, black holes, all mixed together |
| `connection_ids` | `set[ConnectionId]` | `set()` | IDs only — resolve via `Galaxy.connections_for()` / `Galaxy.neighbors()` |
| `resource_summary` | `ResourceInventory` | empty | aggregate of every object's `resources` in this system, computed once by `ResourceAggregation.update_system()` during generation |
| `controlled_by` | `CivilizationId \| None` | `None` | which civilization, if any, has claimed the *system* (separate from any individual planet's `control` — see [Where information lives](#where-information-lives)) |

Read helpers: `objects_of_type(cls)` (generic filter over `objects`), `planets()`, `moons()`,
`asteroid_belts()` (all built on `objects_of_type`), `habitable_planets(threshold=0.5)`,
`find_planet(planet_id)` (returns `None` if not found), `is_controlled()`.

### Galaxy and Universe

In `domain/galaxy.py` and `domain/universe.py`.

`Galaxy`: `systems: dict[SystemId, StarSystem]` (default `{}`), `connections: dict[ConnectionId,
Connection]` (default `{}`). Methods: `system(id)`, `all_systems()`, `add_system(system)`,
`add_connection(connection)` (also updates both endpoint systems' `connection_ids`),
`connections_for(system)`, `neighbors(system)`, `distance(a, b)`, `nearby(system, max_distance)`.

`Universe`: `galaxies: list[Galaxy]` (default `[]`), `civilizations: list[Civilization]` (default
`[]`) — plus three private indexes built by `reindex()` (called automatically from
`__post_init__`, and safe to call again yourself if you ever mutate `galaxies`/`civilizations`
directly instead of through the normal generation/simulation flow):

- `_systems_by_id: dict[SystemId, StarSystem]`
- `_planets_by_id: dict[StellarObjectId, Planet]`
- `_civilizations_by_id: dict[CivilizationId, Civilization]`

Public read methods: `find_system(id)`, `find_planet(id)`, `civilization(id)` (all raise
`KeyError` if missing — there's no "get-or-None" variant at this layer), `systems()`, `planets()`,
`galaxy()` (returns `galaxies[0]`; the codebase currently assumes a single galaxy throughout,
even though the field is a list).

### Civilizations

In `domain/civilization.py`.

`SimulationEvent` (**frozen**): `time: SimulationTime`, `kind: str` (a free-form label like
`"PlanetColonized"` or `"SystemClaimed"` — see [Add a new simulation
handler](#add-a-new-simulation-handler) for adding your own kinds), `actor_id: str` (currently
always `str(civilization_id.value)`), `data: Mapping[str, object] = {}` (handler-specific payload,
e.g. `{"planet_id": ..., "system_id": ...}`).

`CivilizationHistory`: `events: list[SimulationEvent] = []`, plus `record(event)` and
`events_of_kind(kind)`.

`DiplomacyState`: `relations: dict[CivilizationId, str] = {}` — a stance string per other
civilization (`"neutral"` is the implicit default for anyone not in the dict). Plus
`stance_with(other)` and `is_at_war_with(other)` (true only if the stance is literally `"war"`).
No handler currently writes to this — it exists as an extension point (see the README's "Scope"
section); populate `relations` yourself if you add diplomacy logic.

`CivilizationDevelopment` (in `domain/development.py`, but conceptually part of a civilization):
`technology: float = 1.0`, `industrialization: float = 1.0`, `infrastructure: float = 1.0`,
`population: float = 1.0`, plus `overall_score()` (their average). **Don't confuse this with
`PlanetDevelopment`** — they have similarly-named fields (`infrastructure`, `population`) but
different meanings and different scales: `CivilizationDevelopment` starts at `1.0` and grows
unboundedly (only `technology` currently grows, via `ExplorationHandler`); `PlanetDevelopment`
starts at `0.0` and is capped at `1.0`.

`TradeState` / `TradeRoute` (in `domain/trade.py`): `TradeRoute` — `id: TradeRouteId`,
`civilization_id: CivilizationId`, `source_system_id: SystemId`, `destination_system_id:
SystemId`, `traffic: float`, `capacity: float`, `value: float`, `active: bool = True` (all except
`active` are required, no defaults). `TradeState`: `routes: list[TradeRoute] = []`, plus
`active_routes()` and `total_trade_value()`.

`Civilization`:

| Field | Type | Default | Meaning |
|---|---|---|---|
| `id` | `CivilizationId` | required | |
| `name` | `str` | required | |
| `origin_world_id` | `StellarObjectId` | required | the `Planet.id` this civilization started on |
| `controlled_system_ids` | `set[SystemId]` | `set()` | |
| `controlled_planet_ids` | `set[StellarObjectId]` | `set()` | |
| `resources` | `ResourceInventory` | empty | accumulated stockpile, grown every stellar tick by `ResourceUtilizationHandler` |
| `development` | `CivilizationDevelopment` | new `CivilizationDevelopment()` | |
| `history` | `CivilizationHistory` | new, empty | |
| `diplomacy` | `DiplomacyState` | new, empty | |
| `trade` | `TradeState` | new, empty | |

Plus `is_at_war_with(other_civilization)`, a convenience over `diplomacy.is_at_war_with(other.id)`.

### Configuration objects

All **frozen**, in `config/generation.py` and `config/simulation.py`. These are the only objects
in the project you're expected to construct with keyword arguments directly, rather than reading.

`StarMapConfig`: `star_count: int`, `width: float`, `height: float`, `depth: float = 0.0`
(required fields have no default; pass `depth=0.0` or omit it for a flat 2D map).

`SystemGenerationConfig`: `min_planets: int = 0`, `max_planets: int = 8`,
`min_moons_per_planet: int = 0`, `max_moons_per_planet: int = 3`,
`asteroid_belt_chance: float = 0.2`, `resource_richness: float = 1.0` (a multiplier applied to
every resource quantity rolled during generation).

`ConnectionConfig`: `density: float` (probability, per eligible system pair, that a connection is
proposed), `max_distance: float` (pairs farther apart than this are never connected by the
density pass), `minimum_connections: int = 1` (a post-pass tops up any system left with fewer
connections than this, connecting it to its nearest unconnected neighbors).

`CivilizationSeedConfig`: `civilization_count: int`, `minimum_origin_habitability: float = 0.6`
(the seeder falls back to the *most* habitable planet available in a chosen system if none clears
this bar).

`WorldGenerationConfig`: `stars: StarMapConfig`, `systems: SystemGenerationConfig`,
`connections: ConnectionConfig`, `civilizations: CivilizationSeedConfig` — plus the
`WorldGenerationConfig.default()` static constructor (200 stars, default system/civilization
settings, `ConnectionConfig(density=0.05, max_distance=80.0)`, 6 civilizations).

`SimulationConfig`: `stellar_tick_length: Duration = Duration(1)`,
`interstellar_tick_length: Duration = Duration(100)`, `validate_after_tick: bool = False` — plus
`SimulationConfig.standard()` (identical to the defaults; kept for symmetry with
`WorldGenerationConfig.default()` and as a stable name to call out from application code).

### Simulation runtime objects

In `simulation/clock.py`, `simulation/context.py`, `simulation/engine.py` — these exist only
while a simulation is running; nothing here is part of the persisted `Universe`.

`SimulationClock` (**not frozen** — advanced in place): `current_time: SimulationTime =
SimulationTime(0)`, `stellar_interval: Duration = Duration(1)`, `interstellar_interval: Duration =
Duration(100)`. `advance_stellar()` adds `stellar_interval` to `current_time`;
`advance_interstellar()` (defined but not called by `SimulationRun.run` — see below) would add
`interstellar_interval`.

`StellarTickContext` / `InterstellarTickContext`: identical shape, `universe: Universe`, `clock:
SimulationClock`, `rng: RandomSource` — the one object every handler's `execute()` receives.
Having two distinct types (rather than one shared context) is what lets `StellarTickHandler` and
`InterstellarTickHandler` be declared as separate `Protocol`s, so a handler can't accidentally be
registered on the wrong list.

`SimulationEngine` (**not frozen**): `stellar_handlers: list[StellarTickHandler] = []`,
`interstellar_handlers: list[InterstellarTickHandler] = []` — plus the `standard(id_sequence)`
static constructor described in [`simulation/`](#simulation) above.

`SimulationRun` (a plain class, not a dataclass) holds `clock` (public), plus private `_engine`,
`_universe`, `_config`, `_validator`, `_stellar_rng`, `_interstellar_rng`. Note
`SimulationRun.run()` only ever calls `clock.advance_stellar()` — every stellar tick advances
time by `stellar_tick_length`, and interstellar handlers simply run periodically on that same
timeline (every `interstellar_tick_length // stellar_tick_length` stellar ticks) rather than
advancing time a second time.

### Procedural output objects

In `procedural/cities.py`, `procedural/planet_details.py`, `procedural/traffic.py` — these are
return values only. Nothing in the domain layer ever holds a reference to one of these.

`City` (**frozen**): `name: str`, `population: int`, `technology_level: float`,
`infrastructure_score: float`.

`PlanetDetails`: `cities: list[City] = []`, `population: int = 0`,
`infrastructure_score: float = 0.0`. `population` is the sum of `cities`' populations when there
are any cities, otherwise a fallback derived directly from `planet.control.development.population
* 1_000_000`.

`DetailLevel` — an `Enum`: `MINIMAL` (skip city generation entirely — `cities` will be empty),
`STANDARD`, `RICH` (currently `STANDARD` and `RICH` behave identically; the distinction is an
extension point for a future, more detailed generator).

`TrafficProfile` (**frozen**): `estimated_ships: int`, `congestion: float` (0–1, `connection_count
/ 8` capped at `1.0`).

## Where information lives

A lookup table for "I need X — where do I actually read it from?" Paths assume you have a `world:
World` and, where relevant, a `civilization: Civilization`, `planet: Planet`, or `system:
StarSystem` already in hand.

| Question | Where | Notes |
|---|---|---|
| Who owns this planet? | `planet.owner` (or `planet.control.civilization_id`) | `None` if unclaimed |
| What civilization controls this system? | `system.controlled_by` | Set only by `ExpansionHandler` when a civilization claims the system as a whole — **independent** of any individual planet's `control` inside it. A system can be `controlled_by` a civilization with zero colonized planets in it yet, or vice versa during the gap before expansion catches up. |
| Which planets does a civilization control? | `civilization.controlled_planet_ids` (IDs) → `world.controlled_planets(civilization)` (objects) | |
| Which systems does a civilization control? | `civilization.controlled_system_ids` (IDs) → `world.controlled_systems(civilization)` (objects) | |
| What's a civilization's origin world? | `civilization.origin_world_id` → `world.origin_world(civilization)` | |
| How much of resource X is *available* in a system? | `system.resource_summary.amount(resource)` | Computed once at generation time by `ResourceAggregation.update_system()`. **Not depleted** by simulation — it represents the system's total endowment, not a shrinking stockpile. |
| How much of resource X has a civilization actually *extracted*? | `civilization.resources.amount(resource)` | Grows every stellar tick via `ResourceUtilizationHandler`, at a rate proportional to `system.resource_summary` for each controlled system. Uncapped — can exceed the system's nominal endowment over a long simulation. |
| What's a planet's population? | `planet.control.development.population` | A normalized **0–1 score**, not a headcount. For an actual number, call `world.details.for_planet(planet)` and read `PlanetDetails.population`. |
| What's a civilization's tech/industry level? | `civilization.development` (`CivilizationDevelopment`) | Distinct from, and not directly derived from, any individual planet's `PlanetDevelopment` — see the warning in [Civilizations](#civilizations). |
| How fast is a civilization expanding? | `world.spreading_power(civilization)` | Computed on demand by the injected `SpreadingRateCalculator`, not stored anywhere. |
| Are two civilizations at war? | `civilization.diplomacy.relations` / `civilization.is_at_war_with(other)` | Nothing currently writes to this automatically — see [Civilizations](#civilizations). |
| What trade routes does a civilization have? | `civilization.trade.routes` / `civilization.trade.active_routes()` | Created by `TradeRouteHandler` → `NeighboringSystemTradePolicy` during interstellar ticks. |
| What has happened to a civilization over time? | `civilization.history.events` / `civilization.history.events_of_kind(kind)` | Currently populated with `"PlanetColonized"` (by `LocalColonizationHandler`) and `"SystemClaimed"` (by `ExpansionHandler`). |
| How are two systems connected, and by how much? | `Connection` objects live in `galaxy.connections`, keyed by `ConnectionId` | `StarSystem` only stores `connection_ids` (the keys) — use `galaxy.connections_for(system)` or `galaxy.neighbors(system)` rather than reading `connection_ids` directly. |
| What's in a system? | `system.stars` (list of `Star`, almost always length 1) is **separate** from `system.objects` (everything else — `Planet`, `Moon`, `AsteroidBelt`, `Nebula`, `BlackHole`, all mixed together in one list) | Use `system.planets()`, `system.moons()`, `system.asteroid_belts()`, or `system.objects_of_type(YourClass)` rather than filtering `objects` by hand. |
| Which moons belong to a planet, and which planet does a moon belong to? | Two separate pointers that must agree: `planet.moon_ids` (list of `StellarObjectId`) and `moon.parent_planet_id` | Generation keeps these in sync; nothing enforces it automatically if you mutate the graph yourself. |
| What time is it in the simulation? | `simulation.clock.current_time` (a `SimulationRun`'s public `clock` attribute) | Not stored on `Universe` — time only exists while a `SimulationRun` is active. |
| Where does the simulation's randomness come from? | Not stored on any domain object | `SimulationRun` holds two private `SeededRandom` streams (`"simulation.stellar"`, `"simulation.interstellar"`), created once at construction from the `World`'s seed. |
| How do I look up a system/planet/civilization by ID? | `world.find_system(id)`, `world.find_planet(id)`, `world.civilization(id)` | Thin wrappers over `Universe`'s private `_systems_by_id` / `_planets_by_id` / `_civilizations_by_id` indexes, rebuilt by `Universe.reindex()`. |
| Where does the `IdSequence` used during generation go afterwards? | `world.id_sequence` | Kept alive on `World` so simulation-time ID minting (e.g. new `TradeRoute`s) continues from where generation left off, with no collisions. |

## Common recipes

### Generate a world

```python
from sla_world import WorldBuilder, WorldGenerationConfig
from sla_world.config.generation import (
    StarMapConfig, SystemGenerationConfig, ConnectionConfig, CivilizationSeedConfig,
)

config = WorldGenerationConfig(
    stars=StarMapConfig(star_count=100, width=200.0, height=200.0, depth=200.0),
    systems=SystemGenerationConfig(max_planets=5, resource_richness=1.2),
    connections=ConnectionConfig(density=0.05, max_distance=50.0),
    civilizations=CivilizationSeedConfig(civilization_count=4),
)

world = WorldBuilder.default().with_seed(1234).build(config)
```

Omit `config` to use `WorldGenerationConfig.default()`. The same seed with the same config
always reproduces the same world.

### Run a simulation

```python
from sla_world import SimulationConfig

simulation = world.simulation(SimulationConfig(validate_after_tick=True))
simulation.run(until=5_000)

print(simulation.clock.current_time)
```

`validate_after_tick=True` runs `UniverseValidator` after every tick and raises `RuntimeError`
immediately if an invariant is broken — useful while developing a new handler, expensive to leave
on for large, long-running simulations.

### Read planet and system state

```python
for system in world.systems():
    print(system.name, system.resource_summary.total_value())
    for planet in system.planets():
        print(" ", planet.name, planet.planet_type, planet.habitability.base_score, planet.owner)
```

### Generate on-demand detail

```python
from sla_world.procedural.planet_details import DetailLevel

for civilization in world.civilizations():
    origin = world.origin_world(civilization)
    details = world.details.for_planet(origin, DetailLevel.RICH)
    print(civilization.name, details.population, [c.name for c in details.cities])

system = world.systems()[0]
traffic = world.details.traffic_for(system)
print(traffic.estimated_ships, traffic.congestion)
```

### Swap in your own rule

Every rule type is a `Protocol`, so any object with a matching method works — no base class
required:

```python
from sla_world.domain.civilization import Civilization
from sla_world.domain.universe import Universe

class FlatSpreadingRate:
    def calculate(self, civilization: Civilization, universe: Universe) -> float:
        return 1.0

world = WorldBuilder.default().with_seed(1).build()
world._spreading_rate_calculator = FlatSpreadingRate()
```

To use a custom rule from the start of a simulation, inject it into the handler that consumes it
and hand a custom-built `SimulationEngine` to `SimulationRun` yourself instead of going through
`World.simulation()`:

```python
from sla_world.simulation.engine import SimulationEngine, SimulationRun
from sla_world.simulation.interstellar.expansion import ExpansionHandler
from sla_world.simulation.interstellar.trading import TradeRouteHandler
from sla_world.simulation.systems.resource_utilization import ResourceUtilizationHandler
from sla_world.simulation.systems.development import PlanetaryDevelopmentHandler
from sla_world.simulation.systems.colonization import LocalColonizationHandler
from sla_world.simulation.systems.exploration import ExplorationHandler
from sla_world.config.simulation import SimulationConfig

engine = SimulationEngine(
    stellar_handlers=[
        ResourceUtilizationHandler(),
        PlanetaryDevelopmentHandler(),
        LocalColonizationHandler(),
        ExplorationHandler(),
    ],
    interstellar_handlers=[
        ExpansionHandler(spreading_rate_calculator=FlatSpreadingRate(), expansion_threshold=0.2),
        TradeRouteHandler(world.id_sequence),
    ],
)
simulation = SimulationRun(engine=engine, universe=world.universe, config=SimulationConfig(), seed=world.seed)
simulation.run(until=1_000)
```

### Add a new simulation handler

Any object with an `execute(context)` method is a valid handler — implementing the `Protocol` is
optional, but doing so gets you type-checking:

```python
from sla_world.simulation.ticks import StellarTickHandler
from sla_world.simulation.context import StellarTickContext

class RandomEventHandler(StellarTickHandler):
    def __init__(self, chance: float = 0.001) -> None:
        self._chance = chance

    def execute(self, context: StellarTickContext) -> None:
        for civilization in context.universe.civilizations:
            if context.rng.random() < self._chance:
                civilization.development.population *= 0.95
```

Add it to `SimulationEngine.stellar_handlers` (or build your own engine as shown above).

### Add a new stellar object type

Subclass `StellarObject`; all inherited fields (`id`, `name`, `mass`, `radius`, `resources`)
already have the right defaults or requirements to satisfy dataclass field ordering:

```python
from dataclasses import dataclass
from sla_world.domain.stellar_objects import StellarObject

@dataclass
class DerelictStation(StellarObject):
    faction_origin: str = "unknown"
```

If you want it to show up in generation, add a `_generate_derelict_station` step to
`SystemGenerator.generate` (or subclass `SystemGenerator` and override `generate`), following
the pattern used for `_generate_asteroid_belt`.

### Validate universe invariants

```python
from sla_world.rules.consistency import UniverseValidator

report = UniverseValidator().validate(world.universe)
if not report.is_valid:
    for issue in report.issues:
        print(issue)
```

## Conventions

- **IDs, not embedded references.** `StarSystem`, `Civilization`, and `Planet` all store sets or
  lists of IDs for their relationships, never other domain objects directly. Resolve IDs through
  `Universe` (`find_system`, `find_planet`, `civilization`) or `Galaxy` (`neighbors`,
  `connections_for`). This keeps equality, serialization, and mutation simple and avoids stale
  copies.
- **Policies are `Protocol`s, not base classes.** Anything with the right method signature can be
  passed in — no need to inherit from anything to write a custom rule or handler.
- **Generation is pure given its inputs.** Every generator takes an explicit `IdSequence` and
  `RandomSource`; none of them reach for global state. If a generation step looks
  non-deterministic, check that its `RandomStreams.stream(name)` name isn't accidentally reused
  elsewhere.
- **Procedural output is never written back onto domain objects.** If you find yourself wanting
  to cache a `PlanetDetails` on a `Planet`, don't — keep persisted state in `Control` /
  `PlanetDevelopment` and let procedural generators keep deriving from it.
- **Two different "development" concepts share field names on purpose, but mean different
  things.** `CivilizationDevelopment` (civilization-wide, starts at `1.0`, effectively unbounded)
  and `PlanetDevelopment` (per-planet, starts at `0.0`, capped at `1.0`) both have an
  `infrastructure` field, for example — always check which object you're reading it off of.

## Testing and type-checking

There's no test suite bundled yet — `demo.py` currently serves as the smoke test. When adding
one, favor testing `rules/` and `procedural/` in isolation (they're pure functions of their
inputs) and use a fixed-seed `WorldBuilder` for anything that needs a populated `Universe`.

```bash
python3 -m mypy sla_world --ignore-missing-imports
```

The whole package is fully type-hinted; keep it that way — mypy should report zero errors before
you open a PR.
