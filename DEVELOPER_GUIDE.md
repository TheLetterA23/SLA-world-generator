# Developer Guide

This guide is for anyone extending `sla_world`: adding a new resource, a new kind of stellar
object, a new simulation mechanic, a new rule, or a new piece of procedural detail. It assumes
you've read the top-level `README.md` once, but repeats what you need here so you don't have to
keep flipping between documents.

Read sections 1–3 first no matter what you're building — they explain the dependency rules that
every other section relies on. Then jump to whichever cookbook entry in section 8 matches your
task.

1. [Mental model](#1-mental-model)
2. [Project layout](#2-project-layout)
3. [The dependency rule](#3-the-dependency-rule)
4. [Where data lives](#4-where-data-lives)
5. [The generation pipeline](#5-the-generation-pipeline)
6. [How the simulation works internally](#6-how-the-simulation-works-internally)
7. [The rules layer](#7-the-rules-layer)
8. [Cookbook: adding features](#8-cookbook-adding-features)
9. [Testing](#9-testing)
10. [Pitfalls](#10-pitfalls)
11. [Not implemented yet](#11-not-implemented-yet)

---

## 1. Mental model

Three things happen at different times, and the codebase is split around that:

| When | What | Package |
|---|---|---|
| Once, at world creation | Build a galaxy, systems, planets, connections, and starting civilizations | `generation/` |
| Repeatedly, over simulated time | Civilizations extract resources, grow, colonize, expand, trade | `simulation/` |
| On demand, whenever someone looks | Derive cities, population, traffic for a specific planet/system | `procedural/` |

Everything generation and simulation touch is **persistent state**, held in `domain/` objects
inside a `Universe`. Everything procedural produces is **derived and disposable** — call it again
and you get a fresh (deterministic, but not stored) answer.

A fourth package, `rules/`, holds the actual decision-making logic (how habitable is this planet
for this civilization? should this civilization expand this tick?) as small, swappable classes.
Both `simulation/` and `application.py` call into `rules/` rather than hardcoding decisions
themselves.

## 2. Project layout

```
sla_world/
  __init__.py              # public exports — the surface most callers import from
  application.py           # World facade + DetailServices (what WorldBuilder.build() returns)

  domain/                  # persistent state, zero policy, zero randomness
    values.py               # Position, SimulationTime, Duration
    resources.py             # ResourceType, ResourceAmount, ResourceInventory
    stellar_objects.py       # StellarObject base + Star, Moon, AsteroidBelt, Nebula, BlackHole
    planet.py                 # PlanetType, Atmosphere, HabitabilityProfile, Control, Planet
    connection.py             # Connection (an edge between two systems)
    system.py                  # StarSystem
    galaxy.py                   # Galaxy (systems + connections, with graph helpers)
    civilization.py              # Civilization, DiplomacyState, CivilizationHistory
    development.py                # CivilizationDevelopment
    trade.py                       # TradeRoute, TradeState
    universe.py                     # Universe (top-level aggregate + lookup indexes)

  config/
    generation.py            # StarMapConfig, SystemGenerationConfig, ConnectionConfig, ...
    simulation.py             # SimulationConfig

  generation/               # one-time world construction, composed by WorldBuilder
    star_map_generator.py    # places star systems in space, names them
    system_generator.py       # populates a system with a star, planets, moons, belts
    connection_generator.py    # links systems together
    civilization_seeder.py      # picks origin systems/planets, creates starting civilizations
    world_builder.py             # orchestrates the four generators above, returns a World

  rules/                    # swappable decision-making, no state of its own
    habitability.py          # HabitabilityEvaluator
    spreading.py               # SpreadingRateCalculator
    colonization.py             # ColonizationTargetSelector
    trade.py                     # TradeRoutePolicy
    consistency.py                 # UniverseValidator (invariant checks)

  simulation/               # the tick loop
    clock.py                  # SimulationClock
    context.py                  # StellarTickContext, InterstellarTickContext
    ticks.py                      # StellarTickHandler / InterstellarTickHandler protocols
    engine.py                      # SimulationEngine, SimulationRun
    systems/                        # stellar-tick handlers (run every tick, act within a system)
      resource_utilization.py
      development.py
      colonization.py
      exploration.py
    interstellar/                    # interstellar-tick handlers (run every N ticks, act across systems)
      expansion.py
      trading.py

  procedural/               # derived, on-demand, not persisted
    cities.py                 # City, CityGenerator
    planet_details.py           # PlanetDetails, PlanetDetailGenerator, DetailLevel
    traffic.py                    # TrafficProfile, TrafficEstimator

  infrastructure/           # cross-cutting technical concerns
    ids.py                    # SystemId, StellarObjectId, ConnectionId, CivilizationId, TradeRouteId, IdSequence
    random.py                   # RandomSource protocol, SeededRandom, RandomStreams

demo.py                    # runnable end-to-end example
README.md                  # architecture summary and design-doc deltas
DEVELOPER_GUIDE.md         # this file
```

## 3. The dependency rule

Imports only flow one direction. If you're about to add an import that goes against this table,
stop — it means the code belongs in a different layer.

```
infrastructure  <-  domain  <-  rules  <-  simulation  <-  application  <-  generation
                       ^                      ^
                       |______________________|
                            procedural
```

In words:

- **`infrastructure/`** depends on nothing in this project. It's IDs and randomness.
- **`domain/`** depends only on `infrastructure/`. Domain objects are plain dataclasses: they
  hold state, expose small pure query/derivation methods (`planet.is_habitable()`,
  `galaxy.neighbors(system)`), and never import `rules/`, `simulation/`, `procedural/`, or
  `application.py`. If you find yourself wanting a domain object to "know how to" grow, expand,
  or generate detail, that logic goes in `rules/`, `simulation/`, or `procedural/` instead, and
  is handed the domain object to act on.
- **`rules/`** and **`procedural/`** depend on `domain/` and `infrastructure/` only. They read
  and sometimes mutate domain state that's handed to them, but hold no state of their own beyond
  configuration passed into `__init__`.
- **`simulation/`** depends on `domain/`, `rules/`, `infrastructure/`, and `config/`. It does not
  depend on `generation/` or `application.py`.
- **`application.py`** (the `World` facade) depends on `domain/`, `rules/`, `simulation/`,
  `procedural/`, `config/`, `infrastructure/`. It is the layer that wires everything together for
  a caller.
- **`generation/`** depends on everything above, including `application.py` — `WorldBuilder` is
  the only place that constructs a `World`.

This is why, for example, `Civilization` doesn't have a `.spreading_power()` method: computing
that requires walking the whole `Universe` and calling a `rules/` policy, and `domain/` isn't
allowed to depend on `rules/`. Instead `world.spreading_power(civilization)` lives on the `World`
facade in `application.py`, which is allowed to depend on both.

## 4. Where data lives

Everything persistent hangs off one `Universe`:

```
Universe
 |- galaxies: list[Galaxy]                (currently always exactly one galaxy - see below)
 |   `- Galaxy
 |       |- systems: dict[SystemId, StarSystem]
 |       `- connections: dict[ConnectionId, Connection]
 |
 `- civilizations: list[Civilization]
```

A `StarSystem` owns its stellar objects directly (this is the one place the codebase embeds
full objects instead of IDs, because a system's contents are truly part of the system and never
shared or moved independently):

```
StarSystem
 |- stars: list[Star]
 |- objects: list[StellarObject]      # Planet, Moon, AsteroidBelt, Nebula, BlackHole all mixed together
 |- connection_ids: set[ConnectionId] # resolve via Galaxy.connections_for(system)
 |- resource_summary: ResourceInventory  # cached aggregate, rebuilt by ResourceAggregation
 `- controlled_by: CivilizationId | None
```

Use `system.planets()`, `system.moons()`, `system.asteroid_belts()` rather than filtering
`system.objects` yourself — they use `objects_of_type()`, which is the generic, type-safe way to
pull a subset out of that mixed list.

**Everything that refers to something outside its own aggregate stores an ID, not an object.**
`Civilization.controlled_system_ids: set[SystemId]`, `Civilization.controlled_planet_ids:
set[StellarObjectId]`, `Planet.control.civilization_id: CivilizationId`, `StarSystem.controlled_by:
CivilizationId | None`, `Connection.a` / `Connection.b: SystemId`. This is deliberate (see
README's "Notable design decisions"): it keeps aggregates independently serializable and avoids
stale copies. To turn an ID back into an object, go through `Universe`:

```python
system = universe.find_system(some_system_id)
planet = universe.find_planet(some_stellar_object_id)
civilization = universe.civilization(some_civilization_id)
```

`Universe` builds three lookup dicts (`_systems_by_id`, `_planets_by_id`,
`_civilizations_by_id`) in `__post_init__` via `reindex()`. **If you ever construct new
`StarSystem`, `Planet`, or `Civilization` objects and append them into `universe.galaxies[i]` or
`universe.civilizations` after the `Universe` was built, call `universe.reindex()` afterward** —
otherwise `find_system`/`find_planet`/`civilization` won't see them. Simulation handlers that only
*mutate* existing objects (change `.controlled_by`, add to a `set[...]`, etc.) don't need this,
since the indexes already hold a reference to the same objects — this is only for genuinely new
objects.

**IDs** (`infrastructure/ids.py`): `SystemId`, `StellarObjectId`, `ConnectionId`,
`CivilizationId`, `TradeRouteId` are all frozen, single-field dataclasses (`value: int`) —
distinct types so you can't accidentally pass a `CivilizationId` where a `SystemId` is expected,
but they're cheap and hashable so they work fine as dict keys. `StellarObjectId` is used for
*every* stellar object, including planets and moons — there's no separate `PlanetId`/`MoonId`
type (see the README for why: a narrower subclass field type breaks static substitutability).

**Resources**: `ResourceInventory` is an immutable value object — `.add()`, `.remove()`, and
`.merge()` all return a *new* `ResourceInventory` rather than mutating in place:

```python
inventory = ResourceInventory.empty()
inventory = inventory.add(ResourceType.IRON, 50.0)
inventory = inventory.add(ResourceType.IRON, 25.0)   # inventory.amount(ResourceType.IRON) == 75.0
civilization.resources = civilization.resources.add(ResourceType.WATER, 10.0)  # reassign, don't mutate
```

If you write a handler that accumulates resources onto a civilization or planet, always reassign
(`civilization.resources = civilization.resources.add(...)`), never try to mutate the `amounts`
mapping directly.

## 5. The generation pipeline

`WorldBuilder.build()` runs four generators in sequence and wraps the result in a `World`:

```python
def build(self, config: WorldGenerationConfig | None = None) -> World:
    config = config or WorldGenerationConfig.default()
    streams = RandomStreams(self._seed)
    id_sequence = IdSequence()

    galaxy = self._star_map_generator.generate(config.stars, id_sequence, streams.stream("generation.star_map"))

    system_generator = self._system_generator_factory(config.systems)
    system_rng = streams.stream("generation.systems")
    for system in galaxy.all_systems():
        system_generator.generate(system, id_sequence, system_rng)

    self._connection_generator.generate(galaxy, config.connections, id_sequence, streams.stream("generation.connections"))

    civilizations = self._civilization_seeder.seed(galaxy, config.civilizations, id_sequence, streams.stream("generation.civilizations"))

    universe = Universe(galaxies=[galaxy], civilizations=civilizations)
    return World(universe=universe, id_sequence=id_sequence, seed=self._seed)
```

Step by step:

1. **`StarMapGenerator`** — places `star_count` empty `StarSystem`s in space using a
   `SpatialDistribution` (default: `UniformDistribution`, uniform random inside a box). Each
   system gets an id, a procedurally-generated name, and a `Position`. No stars, planets, or
   connections exist yet.
2. **`SystemGenerator`** — runs once per system. Adds one `Star`, a random number of `Planet`s
   (each with a random `PlanetType`, `Atmosphere`, `HabitabilityProfile`, and a random number of
   `Moon`s), and maybe an `AsteroidBelt`. Every stellar object gets a random `ResourceInventory`.
   At the end it calls `ResourceAggregation.update_system(system)`, which merges every object's
   resources (star + planets + moons + belt) into `system.resource_summary` — this cached field
   is what `rules/spreading.py` and `simulation/systems/resource_utilization.py` read from later,
   so if you add a new kind of resource-bearing object, make sure it still gets folded in here
   (`ResourceAggregation` already iterates `system.objects`, so as long as your object is
   appended to `system.objects` it's covered automatically).
3. **`ConnectionGenerator`** — proposes system pairs via a `ConnectionStrategy` (default:
   `DensityBasedConnectionStrategy`, which considers every pair within `max_distance` and rolls
   `density` odds on each), creates a `Connection` for each accepted pair via
   `galaxy.add_connection()` (which also updates both systems' `connection_ids`), then runs
   `_ensure_minimum_connections` to guarantee every system has at least
   `config.minimum_connections` edges by greedily connecting to its nearest unconnected
   neighbors. This step is O(n²) in star count — fine for hundreds of systems, but see
   [section 11](#11-not-implemented-yet) if you're generating tens of thousands.
4. **`CivilizationSeeder`** — picks `civilization_count` origin systems via a
   `CivilizationSeedStrategy` (default: `ScatteredOriginSelection`, uniform random sample among
   systems that have at least one habitable planet), then for each picks the single most
   habitable planet as the origin world, creates a `Civilization`, and sets `planet.control`,
   `civilization.controlled_planet_ids`, `civilization.controlled_system_ids`, and
   `system.controlled_by` accordingly.

**Determinism**: `RandomStreams(seed)` hands out a separately-seeded `SeededRandom` per named
stream (`"generation.star_map"`, `"generation.systems"`, etc.) by hashing
`f"{seed}:{name}"` with SHA-256. This means changing how many random numbers the connection
generator consumes never perturbs which planets the system generator rolled, because they draw
from independent streams. If you add a new generator, give it its own stream name — don't reuse
an existing generator's `rng`.

**A single `IdSequence`** is threaded through every generator call (and stored on `World` as
`world.id_sequence`), so IDs are unique across the whole build *and* the simulation reuses the
same sequence afterward (see `SimulationEngine.standard(self.id_sequence)` in
`application.py`) — this is why new `TradeRoute`s created mid-simulation never collide with IDs
handed out during generation.

## 6. How the simulation works internally

### Two cadences

The design distinguishes **stellar** ticks (fine-grained, run every step — local growth,
extraction, in-system colonization) from **interstellar** ticks (coarse-grained, run every N
stellar ticks — cross-system expansion, trade). `SimulationConfig` controls the ratio:

```python
@dataclass(frozen=True)
class SimulationConfig:
    stellar_tick_length: Duration = Duration(1)
    interstellar_tick_length: Duration = Duration(100)
    validate_after_tick: bool = False
```

`SimulationRun.run(until)` is the loop:

```python
def run(self, until: int) -> None:
    steps_per_interstellar = max(1, self._config.interstellar_tick_length // self._config.stellar_tick_length)
    step_index = 0
    while self.clock.current_time < until:
        self._engine.step_stellar(self._universe, self.clock, self._stellar_rng)
        self.clock.advance_stellar()
        step_index += 1
        if step_index % steps_per_interstellar == 0:
            self._engine.step_interstellar(self._universe, self.clock, self._interstellar_rng)
        self._validate_if_configured()
```

With the defaults, every stellar tick advances the clock by 1 and every 100th stellar tick also
runs the interstellar handlers once (the clock itself is only advanced by
`advance_stellar()` in this loop; `SimulationClock.advance_interstellar()` exists for callers who
want to drive time manually, but the standard loop doesn't call it, to avoid double-counting).

### Handlers, not one big method

`SimulationEngine` is just two ordered lists of handler objects:

```python
@dataclass
class SimulationEngine:
    stellar_handlers: list[StellarTickHandler] = field(default_factory=list)
    interstellar_handlers: list[InterstellarTickHandler] = field(default_factory=list)

    @staticmethod
    def standard(id_sequence: IdSequence) -> "SimulationEngine":
        return SimulationEngine(
            stellar_handlers=[
                ResourceUtilizationHandler(),
                PlanetaryDevelopmentHandler(),
                LocalColonizationHandler(),
                ExplorationHandler(),
            ],
            interstellar_handlers=[
                ExpansionHandler(),
                TradeRouteHandler(id_sequence),
            ],
        )
```

Each handler implements one of two structural `Protocol`s from `simulation/ticks.py`:

```python
class StellarTickHandler(Protocol):
    def execute(self, context: StellarTickContext) -> None: ...

class InterstellarTickHandler(Protocol):
    def execute(self, context: InterstellarTickContext) -> None: ...
```

There's no base class to inherit from — anything with a matching `execute(self, context)` method
satisfies the protocol, including a plain function wrapped in a small class, or a dataclass. The
context objects (`simulation/context.py`) just bundle the three things every handler needs:

```python
@dataclass
class StellarTickContext:
    universe: Universe
    clock: SimulationClock
    rng: RandomSource
```

`SimulationEngine.step_stellar()` builds one `StellarTickContext` and calls `execute()` on every
handler in `stellar_handlers`, in list order — order matters if handlers interact (e.g.
`ResourceUtilizationHandler` runs before `PlanetaryDevelopmentHandler`, so growth calculations can
rely on that tick's freshly-extracted resources already being reflected in civilization state).
There's no strict ordering requirement built into the engine, so if you add a handler that depends
on another handler having already run this same tick, put it later in the list.

The **built-in stellar handlers** (`simulation/systems/`):

- `ResourceUtilizationHandler` — for every system a civilization controls, extracts
  `utilization_rate` (default 2%) of each resource in `system.resource_summary` into
  `civilization.resources` each tick. Note this does **not** deplete `system.resource_summary` —
  that field represents the system's endowment, not a shrinking stockpile; only the
  civilization's accumulated `resources` grow.
- `PlanetaryDevelopmentHandler` — for every planet a civilization controls, nudges
  `planet.control.development`'s four fields (`population`, `infrastructure`, `industry`,
  `urbanization`) up toward 1.0 each tick, at a rate influenced by the planet's habitability and
  the owning civilization's `CivilizationDevelopment`.
- `LocalColonizationHandler` — for every system a civilization controls, asks a
  `ColonizationTargetSelector` (default `MostHabitableRelativeToOrigin`) to pick an uncolonized
  planet in that system and, if one is found, sets its `control` and records a
  `"PlanetColonized"` `SimulationEvent` on `civilization.history`.
- `ExplorationHandler` — a small placeholder that grows `civilization.development.technology`
  by a fixed amount each tick.

The **built-in interstellar handlers** (`simulation/interstellar/`):

- `ExpansionHandler` — computes each civilization's spreading rate via a
  `SpreadingRateCalculator` (default `ResourceBasedSpreadingRate`); if it clears
  `expansion_threshold` (default 0.4), picks a random uncontrolled neighboring system from the
  civilization's frontier and claims it, recording a `"SystemClaimed"` event.
- `TradeRouteHandler` — delegates to a `TradeRoutePolicy` (default
  `NeighboringSystemTradePolicy`), which opens a `TradeRoute` from each controlled system to any
  neighboring system controlled by someone else that doesn't already have a route.

### Randomness during simulation

`SimulationRun` derives exactly two streams from the run's seed —
`"simulation.stellar"` and `"simulation.interstellar"` — shared by all handlers of that cadence
across the whole run. This means the same `(generation seed, simulation seed, until)` always
produces the same outcome (verified by running the same seed twice and diffing civilization
stats — see [section 9](#9-testing)). If you add a handler that needs its own independent stream
(so that adding/removing an unrelated handler earlier in the list doesn't shift its draws),
derive one from a `RandomStreams` you construct with the same seed rather than reusing
`context.rng` for something unrelated to that handler's normal per-tick randomness — `context.rng`
is a shared resource for the whole cadence.

### Invariant checking

If `SimulationConfig(validate_after_tick=True)`, `SimulationRun` calls `UniverseValidator` (from
`rules/consistency.py`) after every tick and raises `RuntimeError` immediately if it finds a
dangling reference (a civilization controlling a system/planet ID that no longer resolves, an
origin world that no longer exists, a connection pointing at a missing system). This is
deliberately expensive (it's O(state size) every tick) and off by default — turn it on while
developing a new handler that mutates ownership, then turn it off for normal runs.

## 7. The rules layer

Every `rules/` module follows the same shape: a `Protocol` describing the interface, plus one or
more concrete implementations. This is what makes handlers swappable without touching
`simulation/` code:

```python
class SpreadingRateCalculator(Protocol):
    def calculate(self, civilization: Civilization, universe: Universe) -> float: ...

class ResourceBasedSpreadingRate:
    def calculate(self, civilization: Civilization, universe: Universe) -> float:
        ...
```

Handlers accept the protocol type in `__init__` and default to the standard implementation:

```python
class ExpansionHandler:
    def __init__(self, spreading_rate_calculator: SpreadingRateCalculator | None = None, expansion_threshold: float = 0.4) -> None:
        self._spreading_rate_calculator = spreading_rate_calculator or ResourceBasedSpreadingRate()
```

To use a different policy, construct the handler yourself and hand it to a custom
`SimulationEngine` instead of `SimulationEngine.standard(...)` — see the cookbook below.

Current rules: `HabitabilityEvaluator` (how good is this planet for this civilization, blending
its own score with similarity to the origin world), `SpreadingRateCalculator` (how fast should
this civilization expand right now), `ColonizationTargetSelector` (which planet in a system
should be colonized next), `TradeRoutePolicy` (which trade routes should exist), and
`UniverseValidator` (is the universe internally consistent).

## 8. Cookbook: adding features

Each recipe names the one or two files you touch and shows the pattern to follow, consistent
with the existing code (type hints, no comments, small composable classes).

### Add a new `ResourceType`

Edit `domain/resources.py`: add the enum member and its base value.

```python
class ResourceType(Enum):
    IRON = auto()
    ...
    ANTIMATTER = auto()

_RESOURCE_BASE_VALUE: Mapping[ResourceType, float] = {
    ...
    ResourceType.ANTIMATTER: 20.0,
}
```

Nothing else needs to change — `_ALL_RESOURCE_TYPES` in `generation/system_generator.py` is
built from `list(ResourceType)`, so the new type is immediately eligible to appear in generated
inventories, and `ResourceInventory.total_value()` picks up the new base value automatically.

### Add a new stellar object type (e.g. a `SpaceStation`)

Edit `domain/stellar_objects.py` — subclass `StellarObject`, giving every new field a default so
it stays constructible after `StellarObject.resources` (which already has a default):

```python
@dataclass
class SpaceStation(StellarObject):
    owner_civilization_id: CivilizationId | None = None
    capacity: int = 0
```

Then generate them somewhere — either add a step to `generation/system_generator.py` (append to
`system.objects`, same pattern as `_generate_asteroid_belt`), or write a standalone stellar
handler that builds them mid-simulation. Either way, nothing else needs to change:
`StarSystem.objects_of_type(SpaceStation)` works immediately, and
`ResourceAggregation.update_system` already folds any `resources` your new object carries into
`system.resource_summary`, since it iterates `system.objects` generically.

### Add a new `PlanetType`

Edit `domain/planet.py`'s `PlanetType` enum, then decide whether it should be treated as
naturally habitable — `generation/system_generator.py`'s `_HABITABLE_PLANET_TYPES` tuple
controls which types get the higher habitability/breathable-atmosphere baseline:

```python
_HABITABLE_PLANET_TYPES = (PlanetType.ROCKY, PlanetType.OCEAN, PlanetType.YOUR_NEW_TYPE)
```

### Change how systems are placed in space

`generation/star_map_generator.py`'s `SpatialDistribution` protocol is the extension point.
Implement a new one (e.g. clustered "spiral arm" placement) and pass it into `WorldBuilder`:

```python
class SpiralArmDistribution:
    def position_for(self, index: int, config: StarMapConfig, rng: RandomSource) -> Position:
        ...

world = WorldBuilder(star_map_generator=StarMapGenerator(SpiralArmDistribution())).with_seed(1).build()
```

### Change how systems get connected

Same pattern: implement `ConnectionStrategy` (`generation/connection_generator.py`) and pass a
`ConnectionGenerator(strategy=YourStrategy())` into `WorldBuilder`.

### Change how civilizations are seeded

Implement `CivilizationSeedStrategy` (`generation/civilization_seeder.py`) — e.g. to force
civilizations to start at a minimum distance from each other — and pass
`CivilizationSeeder(strategy=YourStrategy())` into `WorldBuilder`.

### Swap a rule (e.g. a different colonization target selector)

Write a class satisfying the relevant `Protocol`, then build your own `SimulationEngine` instead
of using `SimulationEngine.standard(...)`:

```python
from sla_world.rules.colonization import ColonizationTargetSelector
from sla_world.simulation.engine import SimulationEngine, SimulationRun
from sla_world.simulation.systems.colonization import LocalColonizationHandler
from sla_world.simulation.systems.resource_utilization import ResourceUtilizationHandler
from sla_world.config.simulation import SimulationConfig

class RichestPlanetFirst:
    def choose(self, civilization, system, universe):
        candidates = [planet for planet in system.planets() if planet.owner is None]
        return max(candidates, key=lambda planet: planet.resource_value(), default=None)

engine = SimulationEngine(
    stellar_handlers=[ResourceUtilizationHandler(), LocalColonizationHandler(RichestPlanetFirst())],
    interstellar_handlers=[],
)
run = SimulationRun(engine=engine, universe=world.universe, config=SimulationConfig(), seed=world.seed)
run.run(until=5_000)
```

(`World.simulation()` always builds the standard engine; for a custom engine, construct
`SimulationRun` directly as above, reusing `world.universe` and `world.seed`.)

### Add a brand-new stellar-tick handler (e.g. random disasters)

Add a file under `simulation/systems/`, implement `execute(self, context: StellarTickContext) ->
None`, then add it to the list in `SimulationEngine.standard()`:

```python
# simulation/systems/disasters.py
from sla_world.simulation.context import StellarTickContext
from sla_world.domain.civilization import SimulationEvent

class DisasterHandler:
    def __init__(self, disaster_chance: float = 0.001) -> None:
        self._disaster_chance = disaster_chance

    def execute(self, context: StellarTickContext) -> None:
        for civilization in context.universe.civilizations:
            for planet_id in civilization.controlled_planet_ids:
                if context.rng.random() > self._disaster_chance:
                    continue
                planet = context.universe.find_planet(planet_id)
                if planet.control is None:
                    continue
                planet.control.development.population *= 0.5
                civilization.history.record(
                    SimulationEvent(time=context.clock.current_time, kind="Disaster", actor_id=str(civilization.id.value), data={"planet_id": planet_id.value})
                )
```

```python
# simulation/engine.py
from sla_world.simulation.systems.disasters import DisasterHandler
...
stellar_handlers=[
    ResourceUtilizationHandler(),
    PlanetaryDevelopmentHandler(),
    LocalColonizationHandler(),
    ExplorationHandler(),
    DisasterHandler(),
],
```

Interstellar handlers follow the identical pattern under `simulation/interstellar/`, implementing
`execute(self, context: InterstellarTickContext) -> None` instead.

### Add a new config field

Config dataclasses are frozen, so add the field with a default so existing callers don't break,
then read it from whichever generator or handler needs it:

```python
@dataclass(frozen=True)
class SystemGenerationConfig:
    ...
    nebula_chance: float = 0.05
```

### Add new procedural, on-demand detail (e.g. `ShipGenerator`)

Follow the `CityGenerator`/`PlanetDetailGenerator` pattern: a small generator class that takes
whatever domain objects it needs plus an `rng`, and returns a plain dataclass — nothing is
written back onto the domain object.

```python
# procedural/ships.py
from dataclasses import dataclass
from sla_world.domain.system import StarSystem
from sla_world.infrastructure.random import RandomSource

@dataclass(frozen=True, slots=True)
class Ship:
    name: str
    class_name: str

class ShipGenerator:
    def generate(self, system: StarSystem, rng: RandomSource) -> list[Ship]:
        if not system.is_controlled():
            return []
        count = int(system.resource_summary.total_value() * 0.002)
        return [Ship(name=f"{system.name} Hull {i+1}", class_name=rng.choice(["Frigate", "Freighter"])) for i in range(count)]
```

Wire it into `DetailServices` in `application.py` the same way `TrafficEstimator` is wired in, so
it's reachable as `world.details.ships_for(system)`. Seed any internal `SeededRandom` from a
stable integer derived from the entity being detailed (see `PlanetDetailGenerator.generate`,
which seeds from `planet.id.value`) so repeated calls for the same entity are stable even though
nothing is persisted.

### Query the world from a script

```python
from sla_world import WorldBuilder, SimulationConfig

world = WorldBuilder.default().with_seed(123).build()
simulation = world.simulation(SimulationConfig(validate_after_tick=True))
simulation.run(until=5_000)

strongest = max(world.civilizations(), key=world.spreading_power)
print(strongest.name, world.spreading_power(strongest))

for system in world.controlled_systems(strongest):
    print(system.name, system.resource_summary.total_value())

for planet in world.controlled_planets(strongest):
    details = world.details.for_planet(planet)
    print(planet.name, details.population, len(details.cities))
```

## 9. Testing

There's no test suite checked in yet — start one with `pytest`. Two things make this codebase
easy to test:

- **Determinism**: any test that builds a world or runs a simulation with a fixed seed will get
  identical results every run, so you can assert exact values instead of ranges:

  ```python
  def test_same_seed_is_deterministic():
      world_a = WorldBuilder.default().with_seed(1).build()
      world_b = WorldBuilder.default().with_seed(1).build()
      assert [s.name for s in world_a.systems()] == [s.name for s in world_b.systems()]
  ```

- **Small configs**: `WorldGenerationConfig` fields are all overridable, so keep test worlds tiny
  (a handful of systems) for speed:

  ```python
  from sla_world.config.generation import WorldGenerationConfig, StarMapConfig, SystemGenerationConfig, ConnectionConfig, CivilizationSeedConfig

  tiny_config = WorldGenerationConfig(
      stars=StarMapConfig(star_count=10, width=50.0, height=50.0, depth=50.0),
      systems=SystemGenerationConfig(max_planets=3),
      connections=ConnectionConfig(density=0.3, max_distance=30.0),
      civilizations=CivilizationSeedConfig(civilization_count=2),
  )
  world = WorldBuilder.default().with_seed(1).build(tiny_config)
  ```

When testing a new rule or handler in isolation, you don't need a full generated world — build
the minimal `Universe`/`StarSystem`/`Civilization` objects by hand and call the class directly
(every rule and handler takes plain domain objects and returns/mutates plain values, with no
hidden global state).

## 10. Pitfalls

- **Don't store domain objects across an aggregate boundary — store the ID.** If you're tempted
  to add a field like `planet.controlling_civilization: Civilization`, store `CivilizationId`
  instead and resolve it through `Universe` when needed. This is what keeps `Universe`'s
  equality/serialization simple and avoids two copies of the same civilization drifting apart.
- **`ResourceInventory` is immutable.** `.add()`/`.remove()`/`.merge()` return new instances;
  forgetting to reassign (`x.add(...)` instead of `x = x.add(...)`) is a silent no-op.
- **Reindex after adding new top-level objects.** Mutating fields on an existing `StarSystem`,
  `Planet`, or `Civilization` (changing `.controlled_by`, appending to a `set[...]`) needs no
  extra step. Only *appending a brand-new `StarSystem`/`Civilization` into `universe.galaxies[i]`
  or `universe.civilizations`* after `Universe.__post_init__` has already run requires calling
  `universe.reindex()` afterward, or lookups won't find it.
- **Give new random draws their own named stream.** Reusing `streams.stream("generation.systems")`
  (or `context.rng` inside a handler) for an unrelated purpose makes your new code's random
  outcomes shift whenever an unrelated earlier call changes how many random numbers it consumes.
  Derive a dedicated stream instead.
- **`system.resource_summary` is a cached aggregate, not a live query.** If you mutate
  `system.objects` or their `.resources` after generation (e.g. a handler that adds a new
  stellar object mid-simulation), call `ResourceAggregation.update_system(system)`
  (`generation/system_generator.py`) again, or the cached summary will be stale.
- **`SimulationConfig.validate_after_tick` is O(universe size) per tick.** Use it while
  developing a handler that touches ownership, not for large production runs.

## 11. Not implemented yet

These are known, intentional gaps (see README "Scope") — good starting points if you want a
larger feature to build:

- **Spatial indexing for connection generation.** `ConnectionGenerator`'s default strategy is
  O(n²) in star count. For very large maps, implement a `ConnectionStrategy` backed by a spatial
  grid or k-d tree and swap it in — the protocol is already there, no engine changes needed.
- **Diplomacy actions.** `DiplomacyState` exists on `Civilization` (a `relations: dict[CivilizationId, str]`
  plus `stance_with`/`is_at_war_with`), but nothing currently changes it — there's no diplomacy
  rule or interstellar handler yet. Follow the `TradeRoutePolicy`/`TradeRouteHandler` pattern.
- **Ships and technology trees.** Deliberately left out per the design document's "avoid
  over-modeling in v1" guidance. If you add them, ships probably belong in `procedural/`
  (derived, like `TrafficEstimator`) unless you want them to persist and be individually
  trackable, in which case they'd need a `domain/` module and ID type of their own, following the
  `StellarObject` pattern.
