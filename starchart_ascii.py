#!/usr/bin/env python3
"""Render a deterministic sla_world galaxy as a polished ANSI/ASCII starchart."""

from __future__ import annotations

import argparse
import math
import string
from collections import defaultdict

from sla_world import WorldBuilder, WorldGenerationConfig
from sla_world.config.generation import StarMapConfig


RESET = "\033[0m"
BOLD = "\033[1m"
COLORS = [
    "\033[91m",
    "\033[92m",
    "\033[93m",
    "\033[94m",
    "\033[95m",
    "\033[96m",
    "\033[97m",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate and render a deterministic sla_world galaxy."
    )
    p.add_argument("seed", type=int)
    p.add_argument("--cols", type=int, default=120)
    p.add_argument("--rows", type=int, default=42)
    p.add_argument("--systems", type=int, default=None)
    p.add_argument(
        "--mode",
        choices=("plain", "civs", "regions"),
        default="plain",
        help=(
            "plain=normal chart, civs=color civilization ownership, "
            "regions=draw territorial hulls around civilizations"
        ),
    )
    p.add_argument("--no-legend", action="store_true")
    p.add_argument("--no-labels", action="store_true")
    p.add_argument("--names", action="store_true")
    p.add_argument("--plain", action="store_true", help="Disable ANSI color.")
    return p.parse_args()


def base62(n: int) -> str:
    chars = string.digits + string.ascii_uppercase + string.ascii_lowercase

    if n < len(chars):
        return chars[n]

    return chars[n // len(chars)] + chars[n % len(chars)]


def cross(o, a, b):
    return (
        (a[0] - o[0]) * (b[1] - o[1])
        - (a[1] - o[1]) * (b[0] - o[0])
    )


def convex_hull(points):
    """Return the perimeter of a set of 2D points."""
    unique = sorted(set(points))

    if len(unique) <= 2:
        return unique

    lower = []

    for point in unique:
        while (
            len(lower) >= 2
            and cross(lower[-2], lower[-1], point) <= 0
        ):
            lower.pop()

        lower.append(point)

    upper = []

    for point in reversed(unique):
        while (
            len(upper) >= 2
            and cross(upper[-2], upper[-1], point) <= 0
        ):
            upper.pop()

        upper.append(point)

    return lower[:-1] + upper[:-1]


def bresenham_points(x0, y0, x1, y1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)

    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1

    err = dx + dy

    while True:
        yield x0, y0

        if x0 == x1 and y0 == y1:
            return

        e2 = 2 * err

        if e2 >= dy:
            err += dy
            x0 += sx

        if e2 <= dx:
            err += dx
            y0 += sy


def scaled_positions(systems, cols, rows):
    xs = [s.position.x for s in systems]
    ys = [s.position.y for s in systems]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    def scale(value, low, high, size):
        if math.isclose(low, high):
            return size // 2

        return round(
            (value - low) / (high - low) * (size - 1)
        )

    width = max(1, cols - 4)
    height = max(1, rows - 5)

    return {
        system.id: (
            2 + scale(system.position.x, min_x, max_x, width),
            2 + (
                height
                - scale(system.position.y, min_y, max_y, height)
            ),
        )
        for system in systems
    }


def draw_line(
    canvas,
    x0,
    y0,
    x1,
    y1,
    char="·",
    overwrite=False,
):
    for x, y in bresenham_points(x0, y0, x1, y1):
        if not (
            0 <= y < len(canvas)
            and 0 <= x < len(canvas[0])
        ):
            continue

        if overwrite or canvas[y][x] == " ":
            canvas[y][x] = char


def draw_hull(canvas, points, char="░"):
    if len(points) < 2:
        return

    if len(points) == 2:
        draw_line(
            canvas,
            *points[0],
            *points[1],
            char,
        )
        return

    for i, a in enumerate(points):
        b = points[(i + 1) % len(points)]

        draw_line(
            canvas,
            *a,
            *b,
            char,
        )


def render(
    world,
    cols,
    rows,
    mode,
    labels,
    use_color,
):
    galaxy = world.universe.galaxy()

    systems = sorted(
        galaxy.all_systems(),
        key=lambda s: s.id.value,
    )

    positions = scaled_positions(
        systems,
        cols,
        rows,
    )

    labels_by_id = {
        system.id: base62(i)
        for i, system in enumerate(systems)
    }

    canvas = [
        [" " for _ in range(cols)]
        for _ in range(rows)
    ]

    cell_color = [
        [None for _ in range(cols)]
        for _ in range(rows)
    ]

    civ_ids = sorted(
        {
            system.controlled_by.value
            for system in systems
            if system.controlled_by is not None
        }
    )

    civ_color = {
        civ_id: COLORS[i % len(COLORS)]
        for i, civ_id in enumerate(civ_ids)
    }

    # Civilization territory boundaries.
    if mode == "regions":
        by_civ = defaultdict(list)

        for system in systems:
            if system.controlled_by is not None:
                by_civ[
                    system.controlled_by.value
                ].append(
                    positions[system.id]
                )

        for points in by_civ.values():
            if len(points) >= 3:
                hull = convex_hull(points)
                draw_hull(canvas, hull)

            elif len(points) == 2:
                draw_hull(canvas, points)

    # Interstellar connections.
    for connection in galaxy.connections.values():
        draw_line(
            canvas,
            *positions[connection.a],
            *positions[connection.b],
            "·",
        )

    # Systems.
    for system in systems:
        x, y = positions[system.id]

        label = (
            labels_by_id[system.id]
            if labels
            else "✦"
        )

        for offset, character in enumerate(label):
            px = x + offset

            if 0 <= px < cols:
                canvas[y][px] = character

                if system.controlled_by is not None:
                    cell_color[y][px] = civ_color[
                        system.controlled_by.value
                    ]

    title = f" S L A   G A L A X Y   //   SEED {world.seed} "

    top = (
        "╭"
        + title.center(cols - 2, "─")[: cols - 2]
        + "╮"
    )

    bottom = "╰" + "─" * (cols - 2) + "╯"

    output = [top]

    for y, row in enumerate(canvas):
        if use_color:
            rendered = []

            for x, character in enumerate(row):
                color = cell_color[y][x]

                if color and character != " ":
                    rendered.append(
                        color + character + RESET
                    )
                else:
                    rendered.append(character)

            text = "".join(rendered)

        else:
            text = "".join(row)

        output.append(
            "│"
            + text[: cols - 2].ljust(cols - 2)
            + "│"
        )

    output.append(bottom)

    return (
        "\n".join(output),
        labels_by_id,
        systems,
        galaxy,
        civ_color,
    )


def main():
    args = parse_args()

    if args.cols < 40:
        raise SystemExit(
            "--cols must be >= 40"
        )

    if args.rows < 12:
        raise SystemExit(
            "--rows must be >= 12"
        )

    config = WorldGenerationConfig.default()

    if args.systems is not None:
        if args.systems < 1:
            raise SystemExit(
                "--systems must be >= 1"
            )

        config = WorldGenerationConfig(
            stars=StarMapConfig(
                star_count=args.systems,
                width=config.stars.width,
                height=config.stars.height,
                depth=config.stars.depth,
            ),
            systems=config.systems,
            connections=config.connections,
            civilizations=config.civilizations,
        )

    world = (
        WorldBuilder.default()
        .with_seed(args.seed)
        .build(config)
    )

    (
        chart,
        labels,
        systems,
        galaxy,
        civ_colors,
    ) = render(
        world,
        args.cols,
        args.rows,
        args.mode,
        labels=not args.no_labels,
        use_color=(
            not args.plain
            and args.mode != "plain"
        ),
    )

    print(chart)

    if args.mode == "civs":
        if not args.plain:
            print(
                f"\n{BOLD}"
                "CIVILIZATION CONTROL"
                f"{RESET}"
            )
        else:
            print("\nCIVILIZATION CONTROL")

        print("--------------------")

        for civilization in world.civilizations():
            controlled = [
                system.name
                for system in systems
                if (
                    system.controlled_by is not None
                    and system.controlled_by.value
                    == civilization.id.value
                )
            ]

            prefix = (
                civ_colors.get(
                    civilization.id.value,
                    "",
                )
                if not args.plain
                else ""
            )

            suffix = RESET if prefix else ""

            print(
                f"{prefix}"
                f"{civilization.name}"
                f"{suffix}: "
                f"{len(controlled)} systems"
            )

    if (
        not args.no_legend
        and not args.no_labels
    ):
        print("\nSYSTEMS")
        print("-------")

        for system in systems:
            if system.controlled_by is not None:
                owner = (
                    f"civ "
                    f"{system.controlled_by.value}"
                )
            else:
                owner = "unclaimed"

            print(
                f"{labels[system.id]:>2}  "
                f"{system.name:<24} "
                f"("
                f"{system.position.x:7.2f}, "
                f"{system.position.y:7.2f}"
                f")  "
                f"{owner:<12} "
                f"links="
                f"{len(system.connection_ids)}"
            )

        print("\nCONNECTIONS")
        print("-----------")

        for connection in sorted(
            galaxy.connections.values(),
            key=lambda c: c.id.value,
        ):
            print(
                f"{labels[connection.a]:>2} "
                f"── "
                f"{labels[connection.b]:<2}  "
                f"distance="
                f"{connection.distance:.2f}"
            )


if __name__ == "__main__":
    main()