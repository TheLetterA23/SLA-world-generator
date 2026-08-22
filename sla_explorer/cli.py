from __future__ import annotations

import argparse
import shutil

from rich.console import Console

from sla_explorer.context import ExplorerSettings, SimulationContext
from sla_explorer.render.civilizations import (
    civilization_table,
    civilization_overview,
    civilization_planet_table,
    civilization_systems_table,
    civilization_history_table,
)
from sla_explorer.render.systems import system_table
from sla_explorer.render.starchart import GalaxyMapRenderer, galaxy_legend_text
from sla_explorer.render.systemchart import SystemChartRenderer


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sla-explorer", description="Explore a deterministically generated SLA universe from a seed."
    )
    parser.add_argument("--seed", type=int, required=True, help="world seed, fully determines generation")
    parser.add_argument("--ticks", type=int, default=5000, help="simulation ticks to run before inspecting the world")
    parser.add_argument("--stars", type=int, default=200, help="number of star systems to generate")
    parser.add_argument("--civilizations", type=int, default=6, help="number of civilizations to seed")

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("civs", help="list all civilizations")

    civ_parser = subparsers.add_parser("civ", help="show details about a single civilization")
    civ_parser.add_argument("name", help="civilization name or #id")
    civ_parser.add_argument("--history", action="store_true", help="show only the history section")
    civ_parser.add_argument("--planets", action="store_true", help="show only the planets section")
    civ_parser.add_argument("--systems", action="store_true", help="show only the systems section")

    subparsers.add_parser("systems", help="list all systems")

    system_parser = subparsers.add_parser("system", help="show a chart for a single system")
    system_parser.add_argument("name", help="system name or #id")

    galaxy_parser = subparsers.add_parser("galaxy", help="print a star chart of the galaxy")
    galaxy_parser.add_argument("--width", type=int, default=None)
    galaxy_parser.add_argument("--height", type=int, default=None)
    galaxy_parser.add_argument("--no-connections", action="store_true", help="omit connection lines")

    subparsers.add_parser("tui", help="launch the interactive terminal UI")

    return parser


def _report_ambiguous(console: Console, kind: str, token: str, matches: list) -> None:
    console.print(f"[yellow]Multiple {kind} named '{token}':[/yellow]")
    for match in matches:
        console.print(f"  #{match.id.value}  {match.name}")
    console.print(f"Use the #id form to disambiguate, e.g. '{kind[:-1]} #{matches[0].id.value}'.")


def _run_civ_command(console: Console, context: SimulationContext, args: argparse.Namespace) -> int:
    matches = context.find_civilization(args.name)
    if not matches:
        console.print(f"[red]No civilization matches '{args.name}'.[/red]")
        return 1
    if len(matches) > 1:
        _report_ambiguous(console, "civilizations", args.name, matches)
        return 1

    civilization = matches[0]
    show_all = not (args.history or args.planets or args.systems)
    console.print(civilization_overview(context, civilization))
    if show_all or args.planets:
        console.print(civilization_planet_table(context, civilization))
    if show_all or args.systems:
        console.print(civilization_systems_table(context, civilization))
    if show_all or args.history:
        console.print(civilization_history_table(context, civilization))
    return 0


def _run_system_command(console: Console, context: SimulationContext, args: argparse.Namespace) -> int:
    matches = context.find_system(args.name)
    if not matches:
        console.print(f"[red]No system matches '{args.name}'.[/red]")
        return 1
    if len(matches) > 1:
        _report_ambiguous(console, "systems", args.name, matches)
        return 1

    system = matches[0]
    renderer = SystemChartRenderer(context)
    console.print(renderer.render_diagram(system))
    console.print(renderer.planet_table(system))
    console.print(renderer.system_summary_table(system))
    return 0


def _run_galaxy_command(console: Console, context: SimulationContext, args: argparse.Namespace) -> int:
    terminal = shutil.get_terminal_size(fallback=(100, 40))
    width = args.width or terminal.columns
    height = args.height or max(terminal.lines - 8, 15)
    renderer = GalaxyMapRenderer(context)
    text, _ = renderer.render(width=width, height=height, show_connections=not args.no_connections)
    chart_console = Console(width=width)
    chart_console.print(text)
    chart_console.print(galaxy_legend_text(context))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    console = Console()

    settings = ExplorerSettings(
        seed=args.seed, ticks=args.ticks, star_count=args.stars, civilization_count=args.civilizations
    )

    console.print(f"[dim]Building universe from seed {settings.seed}, simulating {settings.ticks} ticks…[/dim]")
    context = SimulationContext(settings)

    if args.command in (None, "tui"):
        from sla_explorer.tui.app import SLAExplorerApp

        SLAExplorerApp(context).run()
        return 0

    if args.command == "civs":
        console.print(civilization_table(context))
        return 0

    if args.command == "civ":
        return _run_civ_command(console, context, args)

    if args.command == "systems":
        console.print(system_table(context))
        return 0

    if args.command == "system":
        return _run_system_command(console, context, args)

    if args.command == "galaxy":
        return _run_galaxy_command(console, context, args)

    parser.print_help()
    return 0
