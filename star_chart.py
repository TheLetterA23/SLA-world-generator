import argparse
import matplotlib.pyplot as plt
from sla_world import WorldBuilder


def main():
    parser = argparse.ArgumentParser(
        description="Generate and display a star chart for a galaxy based on seed."
    )
    parser.add_argument("seed", type=int, help="Seed for galaxy generation")
    args = parser.parse_args()

    # Generate the galaxy with the provided seed
    world = WorldBuilder.default().with_seed(args.seed).build()

    # Retrieve all systems
    systems = world.systems()

    # Plot the systems in 2D (x vs y)
    plt.figure(figsize=(8, 8))

    # Draw connections between star systems
    for connection in world.galaxy.connections.values():
        system_a = world.galaxy.system(connection.a)
        system_b = world.galaxy.system(connection.b)

        x1, y1 = system_a.position.x, system_a.position.y
        x2, y2 = system_b.position.x, system_b.position.y

        plt.plot(
            [x1, x2],
            [y1, y2],
            color="gray",
            linewidth=0.8,
            zorder=1,
        )

    # Extract positions for plotting
    xs = []
    ys = []

    for system in systems:
        x, y, z = system.position.x, system.position.y, system.position.z
        xs.append(x)
        ys.append(y)

    # Draw star systems on top of connections
    plt.scatter(
        xs,
        ys,
        s=50,
        color="yellow",
        edgecolors="black",
        zorder=2,
    )

    plt.title(f"Galaxy Star Chart (Seed: {args.seed})")
    plt.xlabel("X Coordinate")
    plt.ylabel("Y Coordinate")
    plt.grid(True)
    plt.axis("equal")

    plt.show()


if __name__ == "__main__":
    main()