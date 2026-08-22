# SLA Explorer

A CLI/TUI tool for inspecting a `sla_world` universe generated from a seed: list and drill into
civilizations (history, controlled planets, controlled systems), browse and search star systems,
view an ASCII/Unicode star chart of the galaxy, and view a per-system orbit diagram.

Given the same `--seed`, generation and simulation are fully deterministic, so the explorer never
needs to persist anything — it just rebuilds the same universe on every run.

## Install

```bash
pip install -e .
```

This installs the `sla-explorer` command (via `[project.scripts]` in `pyproject.toml`), backed by
`rich` and `textual`.

## Usage

```bash
sla-explorer --seed 42                          # launches the interactive TUI
sla-explorer --seed 42 tui                       # same, explicitly

sla-explorer --seed 42 civs                      # table of all civilizations
sla-explorer --seed 42 civ Ilon                  # full detail: overview, planets, systems, history
sla-explorer --seed 42 civ Ilon --history         # just the history section
sla-explorer --seed 42 civ "#1483"                # look up by numeric id (handles duplicate names)

sla-explorer --seed 42 systems                   # table of all star systems
sla-explorer --seed 42 system OrXenRho            # orbit diagram + planet table + system summary

sla-explorer --seed 42 galaxy                     # ASCII/Unicode star chart sized to your terminal
sla-explorer --seed 42 galaxy --width 100 --height 40 --no-connections
```

Global flags (apply to every subcommand, since they control what universe gets built):

- `--seed INT` (required) — the world seed
- `--ticks INT` (default 5000) — how far to run the simulation before inspecting it; `--ticks 0`
  inspects the freshly generated, unsimulated universe
- `--stars INT` (default 200) — number of star systems to generate
- `--civilizations INT` (default 6) — number of civilizations to seed

Without a module install, run it directly from the project root:

```bash
python -m sla_explorer --seed 42
```

## TUI controls

- `↑`/`↓` and `Enter` — navigate lists and tables
- `Escape` — go back a screen (quits from the home screen)
- `Tab` — move focus (e.g. from the systems table to its search box)
- Click a star on the galaxy map to jump straight to that system's chart
- `q` — quit from anywhere

## Screens

- **Home** — world summary (seed, system/civilization counts, simulated time) and a menu
- **Civilizations** — sortable table; select a row for a tabbed detail view
  (Overview / Planets / Systems / History)
- **Systems** — searchable table (type to filter by name); select a row for a system chart
- **Galaxy Map** — a 2D projection of every system's position, colored by owning civilization,
  with faint lines for hyperlane connections; click any star to open it

## Design notes

- `sla_explorer/context.py` builds and simulates the `sla_world` universe once per process and
  exposes name/`#id`-based lookup (civilizations and systems can share a generated name, so exact
  lookups fall back to listing all matches and asking for the `#id` form).
- `sla_explorer/render/` holds plain data-to-`rich`-renderable functions with no Textual
  dependency, so the exact same code produces the CLI's printed tables and the TUI's `Static`
  widget contents — there is only one implementation of "what a civilization/system looks like."
- `sla_explorer/tui/support.py` exists because Textual's `Screen.app` is typed as `App[Any]`, which
  doesn't know about our subclass's `context` attribute; `context_of(screen)` and `row_key_int(key)`
  are small, explicitly-typed helpers so the rest of the TUI code can stay fully type-checked
  rather than relying on `Any`.
- The galaxy chart is a plain character grid (one terminal cell per pixel), so it renders correctly
  in both a piped/non-interactive terminal (CLI) and inside a Textual `Static` widget (TUI) without
  any Textual-specific drawing primitives.
