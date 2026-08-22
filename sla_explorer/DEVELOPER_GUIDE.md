# SLA Explorer — Developer Guide

This is the guide for anyone extending `sla_explorer`: adding a new CLI subcommand, a new TUI
screen, a new column on an existing table, or reacting to a change made in `sla_world`. It assumes
you've skimmed the top-level `README.md` (user-facing usage) and `sla_explorer/README.md`
(feature tour); this document is the "how it's built and why" companion, aimed at the code itself
rather than the CLI surface.

Every code reference below is accurate as of the current tree — file paths, class names, and
signatures are copied from the source, not reconstructed from memory.

---

## 1. What this tool is, and isn't

`sla_explorer` is a **read-only inspector** for a `sla_world` universe. Given a `--seed`, it:

1. builds a universe deterministically via `sla_world.WorldBuilder`,
2. optionally runs the simulation forward a fixed number of ticks,
3. and then lets you look at the result — as tables in a terminal (CLI mode) or as a navigable
   application (TUI mode).

What it deliberately does **not** do:

- **Mutate anything.** No code path in `sla_explorer` calls a setter, appends to a
  `controlled_system_ids` set, or otherwise changes `sla_world` state. Every render function
  takes a `SimulationContext` (or a `World`/domain object) and returns data — never the other way
  around.
- **Persist anything.** There is no database, no save file, no cache directory. Determinism is the
  persistence strategy: the same `--seed` (plus the same `--stars`/`--civilizations`/`--ticks`)
  always reproduces the same universe, so there is nothing to store between runs.
- **Step the simulation interactively.** `SimulationContext.__init__` runs the simulation to
  completion once, up front. There's no "advance one tick" button in the TUI. If you want that,
  see [§8, Known limitations](#8-known-limitations--non-goals) — it's a natural extension, not an
  oversight, but it wasn't needed for an inspection tool.

If you're looking for the simulation engine itself — ticks, handlers, rules, procedural
generation — that all lives in `sla_world`, documented in *its* own README. This guide only covers
the `sla_explorer` package.

---

## 2. Relationship to `sla_world` — the integration contract

### 2.1 Dependency direction

`sla_explorer` depends on `sla_world`. Never the reverse. `sla_world` has zero knowledge that a
CLI or TUI exists — you could delete `sla_explorer` entirely and `sla_world` would still build,
type-check, and run its own `demo.py` unaffected. Keep it that way: if you find yourself wanting
to import something from `sla_explorer` into `sla_world`, that's a sign the thing belongs in
`sla_world` instead (most likely in `sla_world/application.py`, the layer `sla_explorer` already
leans on heavily — see below).

### 2.2 What `sla_explorer` actually imports from `sla_world`

This is the real surface area, grep-verified, not an aspirational list:

| Import | From | Used for |
|---|---|---|
| `World`, `WorldBuilder`, `SimulationConfig`, `WorldGenerationConfig` | `sla_world` (top-level) | building and simulating the universe (`context.py`) |
| `StarMapConfig`, `SystemGenerationConfig`, `ConnectionConfig`, `CivilizationSeedConfig` | `sla_world.config.generation` | translating `ExplorerSettings` into a `WorldGenerationConfig` |
| `Civilization`, `SimulationEvent` | `sla_world.domain.civilization` | rendering civilization rows/history |
| `Planet` | `sla_world.domain.planet` | rendering planet rows |
| `StarSystem` | `sla_world.domain.system` | rendering system rows/charts |
| `PlanetType` | `sla_world.domain.planet` | the planet symbol lookup table in `palette.py` |
| `StellarObjectId`, `SystemId`, `CivilizationId` | `sla_world.infrastructure.ids` | reconstructing typed IDs from raw `int`s (see §2.4) |

That's it. `sla_explorer` never touches `sla_world.simulation.*`, `sla_world.generation.*`
(beyond the config dataclasses), or `sla_world.rules.*` directly — it only calls into them through
the `World` facade (`context.world.spreading_power(...)`, `context.world.simulation(...)`, etc.).
This matters: **`World` (in `sla_world/application.py`) is the entire integration surface**. If a
future `sla_world` refactor keeps `World`'s public methods stable, `sla_explorer` doesn't need to
change even if everything underneath `World` is rewritten.

### 2.3 The single `World` object `sla_explorer` actually calls

Everything `sla_explorer` needs from a built universe goes through these `World` methods
(`sla_world/application.py`):

```python
world.systems() -> list[StarSystem]
world.planets() -> list[Planet]
world.civilizations() -> list[Civilization]
world.find_system(system_id: SystemId) -> StarSystem
world.find_planet(planet_id: StellarObjectId) -> Planet
world.civilization(civilization_id: CivilizationId) -> Civilization
world.controlled_systems(civilization: Civilization) -> list[StarSystem]
world.controlled_planets(civilization: Civilization) -> list[Planet]
world.origin_world(civilization: Civilization) -> Planet
world.spreading_power(civilization: Civilization) -> float
world.simulation(config: SimulationConfig | None = None) -> SimulationRun
world.galaxy  # property -> Galaxy
world.details.for_planet(planet, detail_level=...) -> PlanetDetails
world.details.traffic_for(system) -> TrafficProfile
```

If you're adding a feature to `sla_explorer` and find yourself needing something `World` doesn't
expose (say, a civilization's active trade routes with full route detail, not just the count),
**check whether it's better added to `World` itself** rather than reached for through
`context.world.universe...` directly. `sla_explorer` currently never touches `.universe` — keep it
that way unless there's a good reason; going around the facade is exactly the kind of thing that
breaks silently when `sla_world`'s internals move.

### 2.4 Why IDs get unwrapped to `int` and rewrapped

`sla_world`'s domain IDs (`SystemId`, `CivilizationId`, `StellarObjectId`, ...) are frozen
dataclasses wrapping a single `int` (see `sla_world/infrastructure/ids.py`). They're not visible
to a terminal UI as objects — a `DataTable` row key has to be a plain string, and a
`SimulationEvent.data` payload (`Mapping[str, object]`) stores raw `int`s, not ID objects (see
`sla_world/simulation/systems/colonization.py`, which records
`data={"planet_id": target.id.value, "system_id": system.id.value}`).

So the pattern throughout `sla_explorer` is: **unwrap to `.value: int` to display or store, rewrap
with the ID type to look something up.** Two small helpers exist specifically for the "rewrap"
half, because doing it inline gets both repetitive and mypy-unfriendly:

- `sla_explorer/tui/support.py::row_key_int(row_key: RowKey) -> int` — asserts a `DataTable`
  row key actually has a value (it's typed `str | None` upstream) and converts it to `int`.
- `typing.cast` calls in `sla_explorer/render/civilizations.py::format_event` — `SimulationEvent
  .data` is `Mapping[str, object]`, so pulling `event.data["planet_id"]` back out needs an
  explicit `cast(int, ...)` before it can be wrapped in `StellarObjectId(...)`.

If `sla_world` ever changes `SimulationEvent.data` to store typed IDs instead of raw ints, this is
the first place to update — `format_event` is the only place `sla_explorer` deserializes event
payloads.

### 2.5 Reliance on determinism

`sla_explorer` has no fallback if `WorldBuilder.default().with_seed(seed).build(config)` isn't
deterministic — the entire "no persistence needed" design rests on it. That determinism comes from
`sla_world.infrastructure.random.RandomStreams`, which derives each named stream's seed via
`hashlib.sha256(f"{root_seed}:{name}".encode()).digest()[:8]` rather than Python's built-in
`hash()` (which is randomized per-process for strings unless `PYTHONHASHSEED` is fixed). This is
`sla_world`'s guarantee to keep, not something `sla_explorer` re-verifies — but if you're
debugging a "why did the galaxy change between two runs with the same seed" report, this is where
to look first, and it's very unlikely to be a bug in `sla_explorer` itself. A quick sanity check
that still holds today:

```bash
python -m sla_explorer --seed 99 --ticks 500 --stars 60 --civilizations 3 civs | md5sum
python -m sla_explorer --seed 99 --ticks 500 --stars 60 --civilizations 3 civs | md5sum
# identical hashes
```

### 2.6 What happens if `sla_world`'s domain model grows

A few concrete scenarios, so you're not guessing:

- **New `PlanetType` member added.** `palette.py::_PLANET_SYMBOLS` doesn't have every member —
  `planet_symbol()` falls back to `"o"` for anything missing via `.get(planet_type, "o")`. Nothing
  breaks, but the new type renders indistinguishably from `ROCKY` on system charts until you add a
  symbol for it.
- **New field on `Civilization` or `Planet`.** Nothing breaks (dataclasses don't require every
  field to be consumed), but it also won't show up anywhere until a render function is updated to
  read it. See [§6.2](#62-add-a-new-render-function--table-column).
- **New `SimulationEvent.kind` value.** `format_event()` falls through to `return event.kind`
  (the raw kind string) for anything it doesn't recognize — history tables stay readable, just
  less descriptive. See [§6.4](#64-teach-format_event-about-a-new-simulationevent-kind).
- **A `World` method's signature changes.** This is the one case that *will* break loudly (mypy
  or a runtime `TypeError`), by design — see §2.3. Good, that's the point of going through the
  facade instead of `context.world.universe` directly.

---

## 3. Package layout

```
sla_explorer/
├── __init__.py
├── __main__.py            entry point: `python -m sla_explorer`
├── cli.py                 argparse subcommands, dispatches to render/ or launches the TUI
├── context.py              ExplorerSettings, SimulationContext — builds + simulates the world once
├── palette.py               civilization color assignment, planet-type symbol table
├── render/                 pure data → rich.* renderable functions, ZERO Textual imports
│   ├── civilizations.py
│   ├── systems.py
│   ├── starchart.py        the galaxy map projection/rendering algorithm
│   └── systemchart.py      the per-system orbit diagram algorithm
└── tui/
    ├── app.py               SLAExplorerApp — the Textual App subclass
    ├── app.tcss             stylesheet
    ├── support.py            context_of() / row_key_int() typing helpers (see §2.4, §5.5.2)
    ├── screens/
    │   ├── home.py           HomeScreen — landing menu
    │   ├── civilizations.py CivilizationListScreen, CivilizationDetailScreen
    │   ├── systems.py        SystemListScreen, SystemDetailScreen
    │   └── galaxy.py         GalaxyMapScreen
    └── widgets/
        └── starchart_widget.py  GalaxyMapWidget — the clickable chart Static subclass
```

The `render/` vs `tui/` split is the one architectural rule worth internalizing before you touch
anything:

> **`render/` functions take a `SimulationContext` (and sometimes a domain object) and return a
> `rich.table.Table` / `rich.text.Text` / `rich.panel.Panel`. They never import anything from
> `textual`.** `tui/screens/*.py` call those same functions and hand the result to a `Static`
> widget's `.update(...)`, or manually rebuild an equivalent `DataTable` when a scrollable,
> interactive table is wanted instead of a static one.

This is why `cli.py`'s `civ` subcommand and the TUI's `CivilizationDetailScreen` never drift out
of sync on what a civilization's overview looks like — `civilization_overview()` in
`render/civilizations.py` is the single source of truth, and `cli.py` prints it directly while
`CivilizationDetailScreen._overview_text()`... actually doesn't call it. Which brings up the one
inconsistency worth knowing about:

> **Known duplication:** `CivilizationDetailScreen._overview_text()` (`tui/screens/
> civilizations.py`) re-implements the same six lines that `civilization_overview()`
> (`render/civilizations.py`) already produces, because the TUI wants a plain `str` for a
> `Static` while the CLI wants a `rich.panel.Panel`. If you change what the civilization overview
> shows, **update both.** A cleaner fix — worth doing if you're in this area anyway — is to have
> `civilization_overview()` return the `Text` body alone (no `Panel` wrapper), let the CLI wrap it
> in a `Panel` itself, and have the TUI call `str(body)` or pass the `Text` straight to `Static`
> (which accepts any `RenderableType`, so it doesn't even need to be a plain string).

---

## 4. Control flow: from `--seed` to pixels on screen

```
argv
  │
  ▼
cli.py:_build_parser()          argparse.ArgumentParser + subparsers
  │
  ▼
cli.py:main()
  │  builds ExplorerSettings from --seed/--ticks/--stars/--civilizations
  ▼
context.py:SimulationContext(settings)
  │  1. WorldBuilder.default().with_seed(seed).build(generation_config)  →  World
  │  2. if ticks > 0: world.simulation(SimulationConfig.standard()).run(until=ticks)
  ▼
either:
  ├─ CLI path: render/*.py functions called directly, printed via rich.console.Console
  └─ TUI path: SLAExplorerApp(context).run()
                 │
                 ▼
              HomeScreen (pushed in App.on_mount)
                 │  OptionList → push_screen(...)
                 ▼
        CivilizationListScreen / SystemListScreen / GalaxyMapScreen
                 │  DataTable.RowSelected / OptionList.OptionSelected / click
                 ▼
        CivilizationDetailScreen / SystemDetailScreen
```

Two things worth internalizing about this flow:

- **The universe is built and simulated exactly once per process**, in
  `SimulationContext.__init__`. Every screen, every render call, reads from the same `World`
  instance held on `app.context`. There's no re-fetching, no re-simulating — `context_of(screen)`
  (see §5.5.2) just retrieves that one object.
- **`main()` prints the "Building universe..." message and builds the context before checking
  which subcommand was requested** — including for `tui`. That means `sla-explorer --seed 42`
  with no subcommand pays the generation+simulation cost up front, synchronously, before the
  Textual app even starts (there's no loading screen — see §8).

---

## 5. Layer-by-layer reference

### 5.1 `context.py` — `SimulationContext` & `ExplorerSettings`

```python
@dataclass(frozen=True)
class ExplorerSettings:
    seed: int
    ticks: int = 5000
    star_count: int = 200
    civilization_count: int = 6
    width: float = 500.0
    height: float = 500.0
    depth: float = 500.0
    connection_density: float = 0.05
    connection_max_distance: float = 80.0
```

Only `seed`, `ticks`, `star_count`, and `civilization_count` are exposed as CLI flags today
(`--seed`, `--ticks`, `--stars`, `--civilizations` in `cli.py:_build_parser`). The spatial extent
(`width`/`height`/`depth`) and connection density/range fields exist on the dataclass and are fed
into `WorldGenerationConfig` via `_generation_config()`, but there's no flag wired up to override
them yet — they just take `sla_world`'s effective defaults. If you want `--width`/`--connection-
density`/etc. as CLI flags, this dataclass already has the fields; you only need to add
`argparse` arguments and thread them into the `ExplorerSettings(...)` construction in
`cli.py:main()`.

`SimulationContext` does three things in `__init__`, in order: build the world, run the
simulation (if `ticks > 0`), and record `simulated_time`. `ticks=0` is a deliberate escape hatch —
it inspects the freshly generated, never-simulated universe (every civilization owns only its
origin world, no history events exist yet). Useful for sanity-checking generation in isolation
from the simulation handlers.

**Lookup semantics** — `find_civilization` / `find_system` both:
1. strip whitespace and a leading `#`,
2. if what's left is all digits, match by `.id.value` exactly (at most one match, since IDs are
   unique),
3. otherwise, case-insensitive exact match on `.name`.

There is **no partial/fuzzy matching** — `civ zeth` will not match `Zethese`. This was an explicit
choice: procedurally generated names collide often enough (two civilizations both named
`Zethese` is a real, observed outcome at the default settings) that silently picking "the first
partial match" would be actively misleading. Ambiguity is surfaced, not resolved, by
`cli.py:_report_ambiguous()`, which lists every match with its `#id` and tells the user to
re-run with the `#id` form. If you add fuzzy matching, keep the ambiguity report — don't let it
silently pick one.

### 5.2 `palette.py` — deterministic color assignment

```python
class ColorAssignment:
    def __init__(self, civilizations: list[Civilization]) -> None:
        self._colors = {
            civilization.id: civilization_color(index)
            for index, civilization in enumerate(civilizations)
        }
```

Colors are assigned by **position in the list passed in**, not by any property of the
civilization itself. Every call site constructs `ColorAssignment(context.civilizations())`, and
`SimulationContext.civilizations()` always returns civilizations `sorted(..., key=lambda c:
c.id.value)` — so the assignment is stable across a single process (every screen and every CLI
table agrees on which color is `Ilon`'s), and stable across processes for a given seed (since IDs
are assigned deterministically during generation). It is **not** guaranteed stable if you change
`--civilizations` (a different count changes which civilizations exist, hence their relative
order/count), which is expected and fine — there's no cross-run identity for a civilization beyond
its seed-derived ID.

`_CIVILIZATION_COLORS` has 12 entries; beyond 12 civilizations, colors repeat
(`index % len(_CIVILIZATION_COLORS)`). Two far-apart civilizations sharing a color on the galaxy
map is a real, visible limitation past `--civilizations 12` — see §8.

`_PLANET_SYMBOLS` covers all seven `PlanetType` members that exist today (`ROCKY`, `OCEAN`,
`ICE`, `GAS_GIANT`, `DESERT`, `VOLCANIC`, `BARREN`); `planet_symbol()` still takes a fallback
default (`"o"`) defensively, for the "new `PlanetType` added upstream" scenario from §2.6.

### 5.3 `render/` — the shared rendering layer

#### 5.3.1 `render/civilizations.py`

Two dataclasses (`CivilizationRow`, `PlanetRow`) capture "a row of derived display data" separate
from the raw domain object — `civilization_rows()`/`civilization_planet_rows()` compute these once,
and both the `*_table()` functions (CLI/`Table`) and the TUI screens iterate the same row list.
This is deliberate: **if you need "civilizations sorted by spreading power" or "only planets above
some habitability threshold" for a new feature, add it as a transformation over these row lists,
not as a new traversal of `context.world.civilizations()`.**

`format_event()` is the one function that decodes `SimulationEvent.data` — see §2.4 for why the
`cast(int, ...)` calls are there. It currently recognizes two event kinds
(`"PlanetColonized"`, `"SystemClaimed"`), matching exactly what
`sla_world/simulation/systems/colonization.py` and
`sla_world/simulation/interstellar/expansion.py` emit today. See §6.4 to add a third.

#### 5.3.2 `render/systems.py`

The smallest render module — one function, `system_table()`, which also accepts an optional
`name_filter` for substring filtering. Note that **the CLI's `systems` subcommand doesn't expose
a `--filter` flag** (it always calls `system_table(context)` with the default empty filter) even
though the function supports one — the filter parameter exists because `SystemListScreen._populate
()` in the TUI needed equivalent filtering logic and it made more sense to share it than to
duplicate a `.lower() in .lower()` check. Adding a `--filter` flag to the CLI `systems` subcommand
is a two-line change in `cli.py` if you want it.

#### 5.3.3 `render/starchart.py` — the galaxy map algorithm

This is the most algorithmically involved module, so it's worth walking through in full.

**Projection.** Every `StarSystem.position` is a 3D `Position(x, y, z)` (from
`sla_world.domain.values`), but the chart is 2D — `z` is silently dropped. `GalaxyMapRenderer
.render(width, height, ...)` computes the bounding box of all systems' `x`/`y` from the *actual
generated positions* (not from the `StarMapConfig.width`/`height` the galaxy was generated with),
then linearly maps each system into a `width × height` character grid:

```python
column = int((system.position.x - min_x) / span_x * (width - 1))
row = int((system.position.y - min_y) / span_y * (height - 1))
```

This means the chart always fills the available space exactly, regardless of how sparse or
clustered the galaxy actually is — a tightly clustered galaxy and a sparse one look equally
"full." If you ever want to preserve a sense of actual density/scale (e.g., show empty space as
empty space rather than stretching to fill the frame), this is the function to change, and you'd
want to switch from per-galaxy min/max normalization to a fixed scale factor derived from
`StarMapConfig.width`/`height`/`depth` instead.

**Connections.** `_draw_connections()` walks `galaxy.connections.values()` once, de-duplicating
by `(min(a,b), max(a,b))` pairs (each `Connection` is stored once but touches two systems'
`connection_ids` sets — see `sla_world/domain/galaxy.py:Galaxy.add_connection`), and Bresenham-
plots (`_line_cells()`) a faint `·` (style `"grey35"`) between every connected pair, **only into
cells not already occupied** (`if grid_char[row][column] == " "`). This is why connections are
drawn *before* systems in `render()` — systems always draw on top, never the reverse, so a
system's marker is never overwritten by a connection line even if they land on the same cell.

**No caching, by design.** `render()` rebuilds the entire `width × height` grid (two nested Python
lists) from scratch on every call — there's no memoization keyed on `(width, height,
show_connections)`. For the CLI this is a non-issue (called once). In the TUI,
`GalaxyMapWidget.redraw()` calls it on every `on_resize` event, and `GalaxyMapScreen.on_resize`
calls `redraw()` on every resize — so resizing the terminal window re-runs the full O(width ×
height + connections × line-length) algorithm on every intermediate frame while you drag. At the
default `--stars 200` this is imperceptible; if a future change makes this path expensive (e.g.
per-cell civilization lookups), consider debouncing the resize handler rather than caching the
grid, since terminal size is genuinely the only real input that changes between redraws within a
screen's lifetime.

**Click mapping.** `render()` returns `(Text, dict[(column, row), StarSystem])` as a pair — the
second element is exactly the reverse index `GalaxyMapWidget` needs for `on_click`. If two systems
happen to round to the same cell (entirely possible in a dense galaxy at typical terminal
resolutions), **the later one in iteration order wins** — there's no "nearest system" fallback or
multi-system disambiguation. This is a real, occasionally-visible limitation: clicking a crowded
region of the map can open a different system than the one visually nearest to your click. See §8.

#### 5.3.4 `render/systemchart.py` — the orbit diagram algorithm

`SystemChartRenderer.render_diagram()` draws a **single horizontal line**: `★` for the star, then
for each planet in `system.planets()` order, `spacing` dashes (`─`, styled `"grey35"`) followed by
that planet's symbol (from `palette.planet_symbol()`), colored by owner
(`self._colors.color_for(planet.owner)` — `uncontrolled_color()` when `owner` is `None`, handled
inside `ColorAssignment.color_for`, not by the caller). If the system has any asteroid belts
(`system.asteroid_belts()`), one more dash-run and a `∴` glyph is appended at the end, regardless
of how many belts actually exist — the diagram can show at most one belt marker no matter the
real count (`system_summary_table()`'s "Asteroid belts" row is the accurate count; the diagram is
schematic, not literal).

**This is not real orbital geometry.** `sla_world`'s `Planet` domain object has no orbital radius,
period, or inclination field — planets are ordered exactly as `StarSystem.planets()` returns them,
which is generation order (see `sla_world/generation/system_generator.py`), and `render_diagram
()` spaces them uniformly by `planets.index()`, not by any physical distance. The `#` column in
`planet_table()` and the small numeric labels under the diagram both reflect this same generation-
order index — "planet 3" here means "the third planet `SystemGenerator` created for this system,"
not "the third-closest to the star." If `sla_world` ever adds a real orbital-distance field to
`Planet`, this is the function to update to sort/space by it instead.

**Label alignment is single-digit-safe only.** `label_line.append(str(index).rjust(1), style=
"dim")` right-justifies to a minimum width of 1 — for systems with 10+ planets (possible but
unlikely at the default `max_planets=8` in `sla_world`'s `SystemGenerationConfig`), the two-digit
labels will shift the alignment under the diagram by one column starting at planet 10. Cosmetic,
not a crash; `rjust(2)` on both `label_line` entries and the `spacing` dash-count would fix it if
you increase `max_planets` in a config used with this renderer.

### 5.4 `cli.py` — argparse dispatch

Standard `argparse` with subparsers; nothing unusual in the structure. Two things worth flagging:

- **Global flags come before the subcommand**, not after — `sla-explorer --seed 42 civ Ilon`, not
  `sla-explorer civ --seed 42 Ilon`. This is because `--seed`/`--ticks`/`--stars`/`--civilizations`
  are added to the top-level `parser`, not to each `subparsers.add_parser(...)` — they determine
  *which universe gets built at all*, so they apply uniformly regardless of what you're inspecting
  in it. If you add a new global flag, add it to `parser` in `_build_parser()`, not to an
  individual subcommand's parser, unless it's genuinely subcommand-specific (like `civ`'s
  `--history`/`--planets`/`--systems`).
- **The `galaxy` subcommand constructs its own `Console(width=width)`** (`_run_galaxy_command`)
  rather than reusing the shared `console` passed in. This is a fix for a real bug: `rich.Console`
  auto-detects terminal width and wraps any renderable wider than that at print time, so printing
  a pre-built `width`-character-wide grid through a differently-sized default `Console` silently
  corrupts the chart (each row wraps mid-line onto the next). If you add another fixed-width
  renderable anywhere else, **construct a `Console(width=...)` matching that exact width before
  printing it** — this is not optional cosmetic pickiness, it's the difference between a readable
  chart and a scrambled one.

`_report_ambiguous()` is shared between the `civ` and `system` commands (parameterized by a
`kind: str` like `"civilizations"`/`"systems"` used both in the message and, via `kind[:-1]`, to
suggest the correct singular subcommand name in the follow-up hint). If you add a third
name-or-`#id`-lookup subcommand, reuse this function rather than re-writing the disambiguation
message.

### 5.5 `tui/` — the Textual application

#### 5.5.1 `app.py`

```python
class SLAExplorerApp(App):
    CSS_PATH = Path(__file__).with_name("app.tcss")
    BINDINGS = [Binding("q", "quit", "Quit")]
    TITLE = "SLA Universe Explorer"

    def __init__(self, context: SimulationContext) -> None:
        super().__init__()
        self.context = context

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())
```

`SimulationContext` is passed in already-built — `SLAExplorerApp` never builds or simulates
anything itself; that's `cli.py:main()`'s job (see §4). This keeps the App trivially testable
headlessly (see §7) without needing to spin up a real universe inside every pilot test... except
that the current tests do build a small one anyway, since there's no lighter-weight fixture. If
you write many more TUI tests, a shared `pytest` fixture that builds one small
`SimulationContext` once per test session (rather than once per test) would meaningfully speed up
the suite.

There's no `on_unmount`/cleanup logic and no persistence — quitting the app just exits the
process. `q` is bound globally at the App level; `escape` is bound per-screen (see below) to
either `app.pop_screen` (go back) or `app.quit` (only on `HomeScreen`, since there's nowhere to
pop back *to*).

#### 5.5.2 `support.py` — why it exists

```python
def context_of(screen: Screen) -> SimulationContext:
    return cast(SimulationContext, getattr(screen.app, "context"))


def row_key_int(row_key: RowKey) -> int:
    value = row_key.value
    assert value is not None
    return int(value)
```

Textual's `Screen.app` property is typed as `App[Any]` in the framework itself — it has no way to
know that *our* `App` subclass carries a `.context: SimulationContext` attribute, because
`Screen` isn't generic over the app type that hosts it. Writing `self.app.context` directly is
runtime-correct (it works fine) but mypy-incorrect (`"App[Any]" has no attribute "context"`).
`context_of()` uses `getattr` + `cast` specifically because `getattr(obj, "string-literal")`
doesn't trigger mypy's static attribute check the way `obj.context` does — it's a narrow, explicit
escape hatch for this one known framework limitation, not a general "turn off type checking"
pattern. **Every screen should call `context_of(self)` instead of `self.app.context` directly** —
if you write the latter, it'll work today but reintroduce the mypy error this helper exists to
avoid.

`row_key_int()` exists for a similar reason: `DataTable.RowSelected.row_key` is a `RowKey` whose
`.value` is typed `str | None` (a `DataTable` row doesn't strictly require a key), but every row
`sla_explorer` adds always passes `key=str(...)` explicitly (see `CivilizationListScreen.on_mount`,
`SystemListScreen._populate`), so the `None` case genuinely can't happen at these call sites — the
`assert` documents that invariant rather than silently `int()`-ing a value mypy considers possibly
absent.

#### 5.5.3 `screens/`

**Navigation model.** Every screen but `HomeScreen` binds `escape` to `("escape", "app.pop_screen",
"Back")` — Textual's dotted binding syntax for calling an action on the App rather than the
Screen. `HomeScreen` binds both `escape` and `q` to `app.quit`, since it's the bottom of the
stack. `push_screen(...)` calls always happen from an event handler
(`on_option_list_option_selected`, `on_data_table_row_selected`, or `GalaxyMapWidget`'s
click-forwarded `_open_system`), never from `compose()` or `on_mount()` — screens are pushed in
response to user action, not automatically. If you add a new screen, follow this pattern: bind
`escape` to `app.pop_screen` unless it's genuinely a new "root" the user can reach directly from
`HomeScreen`.

**`HomeScreen`** (`screens/home.py`) is the only screen that imports all three other top-level
screens directly (`CivilizationListScreen`, `SystemListScreen`, `GalaxyMapScreen`) — it's the hub.
Its `OptionList` options carry an `id` (`"civilizations"` / `"galaxy"` / `"systems"`) that
`on_option_list_option_selected` switches on. Adding a fourth menu item means adding an `Option`
here and a branch in that handler — see §6.3 for the full recipe.

**`CivilizationListScreen` / `CivilizationDetailScreen`** (`screens/civilizations.py`). The list
screen is a single `DataTable`; row selection looks up the civilization by ID
(`CivilizationId(row_key_int(event.row_key))`) and pushes the detail screen with the actual
`Civilization` object passed into `__init__` (not just an ID — the detail screen doesn't need to
look anything up itself once constructed). The detail screen uses `TabbedContent`/`TabPane` for
four tabs (Overview / Planets / Systems / History); all four are populated in a single `on_mount`,
not lazily per-tab-activation — for a civilization controlling hundreds of planets this means the
Planets `DataTable` is fully built even if the user never opens that tab. Not a problem at typical
scales (`--civilizations 6`, few dozen planets per civilization); would be worth lazy-loading if
someone runs `--civilizations 2 --stars 2000` and drills into a civilization that owns a large
fraction of the galaxy.

**`SystemListScreen` / `SystemDetailScreen`** (`screens/systems.py`). The list screen adds a
search `Input` above the `DataTable`. **`on_mount` explicitly calls
`self.query_one("#system-table", DataTable).focus()`** — without this, Textual gives focus to the
first focusable widget in composition order, which is the `Input`, and pressing Enter on a
freshly-opened systems list would do nothing (`Input.Submitted` fires, not
`DataTable.RowSelected`) until the user manually `Tab`s to the table. This was a real bug caught
by the pilot test suite, not a hypothetical — see §9. If you add another screen with both a
`DataTable` and an `Input`/other focusable widget, decide deliberately which one should have
initial focus and call `.focus()` on it explicitly; don't rely on composition order.

`SystemDetailScreen.__init__(self, system: StarSystem)` takes the domain object directly, same
pattern as `CivilizationDetailScreen`.

**`GalaxyMapScreen`** (`screens/galaxy.py`) — see §5.5.4 for the widget it wraps.
`on_resize(self, event: events.Resize)` calls `self._chart.redraw()` on every resize event; there's
no debounce (see the caching note in §5.3.3). `_open_system()` is passed into `GalaxyMapWidget`'s
constructor as an `on_select` callback — the widget doesn't import `SystemDetailScreen` itself, it
just calls back into the screen, which owns the navigation decision. This inversion (widget
reports "a system was clicked," screen decides "what happens next") is deliberate: it means
`GalaxyMapWidget` could be reused from a different screen with different click behavior (e.g. "add
to a comparison list" instead of "navigate") without modifying the widget.

#### 5.5.4 `widgets/starchart_widget.py`

```python
class GalaxyMapWidget(Static):
    def __init__(self, renderer: GalaxyMapRenderer, on_select: Callable[[StarSystem], None], **kwargs) -> None:
        ...
    def redraw(self, show_connections: bool = True) -> None:
        width = max(self.size.width, 20)
        height = max(self.size.height, 10)
        text, cells = self._renderer.render(width=width, height=height, show_connections=show_connections)
        self._cells = cells
        self.update(text)

    def on_click(self, event: events.Click) -> None:
        system = self._cells.get((event.x, event.y))
        if system is not None:
            self._on_select(system)
```

`redraw()` sizes the chart to `self.size` — the widget's own content area, already accounting for
any padding/border from `app.tcss` — and stores the returned click-map on `self._cells`, which
`on_click` looks up directly against `(event.x, event.y)`. This works because Textual delivers
`events.Click` to a widget with coordinates **relative to that widget's own content region**, not
the screen — that relative-coordinate behavior is exactly why click mapping is implemented as a
method on this `Static` subclass rather than as a `Screen`-level `on_click` handler with manual
offset math. If you ever refactor this into a `Screen`-level handler, you'll need to reintroduce
that offset calculation yourself (subtract the widget's screen-relative region origin from the
event's screen coordinates) — don't, unless you have a specific reason to.

---

## 6. Extending `sla_explorer` (recipes)

### 6.1 Add a new CLI subcommand

Say you want `sla-explorer --seed 42 trade` to list every civilization's active trade routes.

1. Register the subparser in `cli.py:_build_parser()`:
   ```python
   subparsers.add_parser("trade", help="list active trade routes for every civilization")
   ```
2. Add a render function — put it in `render/civilizations.py` if it's civilization-scoped (which
   trade routes are, per `sla_world`'s `Civilization.trade: TradeState`), following the existing
   `civilization_table()` pattern: take a `SimulationContext`, return a `rich.table.Table`.
3. Add a dispatch branch in `cli.py:main()`, alongside the existing `if args.command == "civs":`
   block:
   ```python
   if args.command == "trade":
       console.print(trade_route_table(context))
       return 0
   ```
4. If it makes sense as a TUI screen too, see §6.3 — but a CLI-only subcommand is a complete,
   valid feature on its own; not everything needs a TUI counterpart.

### 6.2 Add a new render function / table column

Follow the `CivilizationRow`/`PlanetRow` pattern from §5.3.1: if you're adding a *derived* value
(something computed from a domain object plus a `World` query, not a raw field), add it as a field
on the relevant row dataclass and compute it once in the `*_rows()` function, rather than
recomputing it inline in every `*_table()` call and every TUI screen's `on_mount`. This is what
keeps the CLI table and the TUI `DataTable` from silently drifting apart on what they display.

Example — adding "years since colonization" to the civilization planet table, assuming
`sla_world` exposed a `planet.control.established_at`:

```python
@dataclass(frozen=True)
class PlanetRow:
    planet: Planet
    system_name: str
    development_level: float
    established_at: int          # new field


def civilization_planet_rows(context: SimulationContext, civilization: Civilization) -> list[PlanetRow]:
    rows = []
    for planet in context.world.controlled_planets(civilization):
        system_name = "?"
        if planet.parent_system_id is not None:
            system_name = context.world.find_system(planet.parent_system_id).name
        established_at = planet.control.established_at if planet.control else 0
        rows.append(PlanetRow(planet, system_name, planet.development_level, established_at))
    rows.sort(key=lambda row: row.planet.name)
    return rows
```

Then both `civilization_planet_table()` (CLI) and `CivilizationDetailScreen.on_mount()` (TUI, the
Planets tab) add one more `table.add_column(...)`/`row.established_at` to their existing loops —
they already iterate `civilization_planet_rows(context, civilization)`, so the new field is
available at both call sites for free.

### 6.3 Add a new TUI screen

Walking through adding a hypothetical "Trade Routes" screen, reachable from the home menu:

1. **Create the screen file** — `tui/screens/trade.py`, following the `SystemListScreen`
   structure most closely if it's a flat list:
   ```python
   from __future__ import annotations

   from textual.app import ComposeResult
   from textual.screen import Screen
   from textual.widgets import Header, Footer, DataTable

   from sla_explorer.tui.support import context_of
   from sla_explorer.render.trade import trade_route_rows


   class TradeRouteListScreen(Screen):
       BINDINGS = [("escape", "app.pop_screen", "Back")]

       def compose(self) -> ComposeResult:
           yield Header()
           table: DataTable = DataTable(id="trade-table")
           table.cursor_type = "row"
           table.add_columns("Civilization", "From", "To", "Value")
           yield table
           yield Footer()

       def on_mount(self) -> None:
           context = context_of(self)
           table = self.query_one("#trade-table", DataTable)
           for row in trade_route_rows(context):
               table.add_row(row.civilization_name, row.source_name, row.destination_name, f"{row.value:.1f}")
   ```
2. **Wire it into the home menu** (`tui/screens/home.py`):
   ```python
   from sla_explorer.tui.screens.trade import TradeRouteListScreen
   ```
   add an option:
   ```python
   Option("Trade Routes", id="trade"),
   ```
   and a branch:
   ```python
   elif option_id == "trade":
       self.app.push_screen(TradeRouteListScreen())
   ```
3. **If rows should drill into detail**, add `on_data_table_row_selected`, using `row_key_int()`
   from `tui.support` to recover whatever ID you keyed the row with, exactly as
   `CivilizationListScreen`/`SystemListScreen` do.
4. **Style it** — if the default `DataTable { height: 1fr; }` rule in `app.tcss` doesn't fit
   (it applies to every `DataTable` by type selector, so a plain list screen usually needs nothing
   extra), add an ID-scoped rule rather than a type-scoped one, to avoid affecting other screens.

### 6.4 Teach `format_event` about a new `SimulationEvent` kind

If `sla_world` adds a new event kind — say `"TradeRouteEstablished"` — extend
`render/civilizations.py::format_event`:

```python
def format_event(context: SimulationContext, event: SimulationEvent) -> str:
    if event.kind == "PlanetColonized":
        ...
    if event.kind == "SystemClaimed":
        ...
    if event.kind == "TradeRouteEstablished":
        source = context.world.find_system(SystemId(cast(int, event.data["source_system_id"])))
        destination = context.world.find_system(SystemId(cast(int, event.data["destination_system_id"])))
        return f"opened a trade route from {source.name} to {destination.name}"
    return event.kind
```

Match the `data` keys exactly against whatever `sla_world`'s handler actually records (check the
`SimulationEvent(...)` construction site in `sla_world/simulation/`, not this file, for the source
of truth on key names) — a `KeyError` here surfaces as a crash the first time that event kind is
hit, not at import time, since `event.data` is an untyped `Mapping[str, object]`.

### 6.5 React to `sla_world` domain changes

If you're the one changing `sla_world` and wondering what in `sla_explorer` might need a matching
update, check §2.2's import table first — anything not in that table can't be affected. Beyond
that, the specific "will silently degrade rather than crash" cases are cataloged in §2.6; anything
not covered there (e.g., removing or renaming a method on `World`) will surface as an immediate
`AttributeError`/`TypeError`, which — per §2.3 — is the intended failure mode for changes to the
integration surface.

---

## 7. Testing

There is no `pytest` suite checked in yet — verification so far has been direct interactive
scripts. Two testing approaches were used during development and are worth formalizing if this
project grows:

**CLI smoke tests** — run each subcommand and check the exit code / grep the output:
```bash
python -m sla_explorer --seed 42 --ticks 3000 --stars 120 --civilizations 5 civs
python -m sla_explorer --seed 42 --ticks 3000 --stars 120 --civilizations 5 civ "#<some-id>"
python -m sla_explorer --seed 42 --ticks 3000 --stars 120 --civilizations 5 system <some-name>
python -m sla_explorer --seed 42 --ticks 3000 --stars 120 --civilizations 5 galaxy --width 90 --height 30
```
Determinism can be checked by hashing output across two runs with identical arguments (§2.5).

**TUI tests** — Textual ships a headless pilot harness (`App.run_test()`) that doesn't need a real
terminal, which is how every screen and interaction in this project was actually verified:

```python
import asyncio
from sla_explorer.context import ExplorerSettings, SimulationContext
from sla_explorer.tui.app import SLAExplorerApp

async def main() -> None:
    context = SimulationContext(ExplorerSettings(seed=42, ticks=3000, star_count=120, civilization_count=5))
    app = SLAExplorerApp(context)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert type(app.screen).__name__ == "HomeScreen"

        options = app.screen.query("OptionList").first()
        options.highlighted = 0
        await pilot.press("enter")
        await pilot.pause()
        assert type(app.screen).__name__ == "CivilizationListScreen"
        # ... etc.

asyncio.run(main())
```

Key things learned writing these that aren't obvious from Textual's docs on first read:

- `DataTable.cursor_row` has **no setter** — use `table.move_cursor(row=N)`.
- `DataTable.clear()` defaults to `columns=False` (clears rows, keeps columns) — this is what
  `SystemListScreen._populate()` relies on to re-filter without re-adding column headers.
- Simulating a terminal resize is `pilot.resize_terminal(width, height)`, not an `App`-level
  method.
- `OptionList` selection in a test is set via `.highlighted = <index>` then `pilot.press("enter")`
  — there's no direct "select option N" pilot helper.

If you formalize this into `pytest`, wrap the `async with app.run_test(...)` block per test
function; a session-scoped fixture that builds one shared `SimulationContext` (generation +
simulation is the slow part, not the Textual interaction) would cut test suite time significantly
versus rebuilding a universe per test.

---

## 8. Known limitations / non-goals

These are documented so they're not mistaken for bugs, and so anyone picking this up knows exactly
where the edges are:

- **No live/streaming simulation view.** The universe is simulated once, fully, before any screen
  renders. There's no "watch it evolve" mode. Adding one would mean either (a) running the
  simulation in a background `asyncio` task and having screens re-read `context.world` on a timer,
  or (b) exposing `SimulationRun.run(until=...)` incrementally from a TUI action — both are
  plausible, neither is implemented.
- **No persistence.** By design (§2.5) — but it does mean there's no "bookmark this civilization"
  or "export this galaxy map as an image" feature, since nothing is ever written to disk.
- **Galaxy map click resolution is cell-granular, not system-nearest.** Dense clusters can have
  the "wrong" (but still real) system open on click — see §5.3.3.
- **No cross-galaxy support.** `sla_world.Universe` supports multiple `Galaxy` instances
  (`universe.galaxies: list[Galaxy]`), but `World.galaxy` (the property `sla_explorer` exclusively
  uses) always returns `galaxies[0]`. `sla_explorer` has no way to view a second galaxy even if
  `sla_world` generated one — not currently possible via `WorldBuilder` anyway, but worth knowing
  if that changes.
- **Colors repeat past 12 civilizations** (§5.2) and **orbit diagram labels misalign past 9
  planets** (§5.3.4) — both cosmetic, both documented at their source above.
- **`CivilizationDetailScreen`'s Planets/Systems/History tabs are all populated eagerly** on
  mount, regardless of which tab is active (§5.5.3) — a scale concern only at unusually large
  `--civilizations`/`--stars` ratios.
- **No `--filter` flag on the `systems` CLI subcommand** despite `system_table()` supporting one
  (§5.3.2) — trivial to add, just not wired up yet.
