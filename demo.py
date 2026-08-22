from __future__ import annotations

from sla_world import WorldBuilder, WorldGenerationConfig, SimulationConfig
from sla_world.config.generation import StarMapConfig, SystemGenerationConfig, ConnectionConfig, CivilizationSeedConfig

config = WorldGenerationConfig(
    stars=StarMapConfig(star_count=150, width=300.0, height=300.0, depth=300.0),
    systems=SystemGenerationConfig(max_planets=6),
    connections=ConnectionConfig(density=0.06, max_distance=60.0, minimum_connections=1),
    civilizations=CivilizationSeedConfig(civilization_count=5),
)

world = WorldBuilder.default().with_seed(42).build(config)

print(f"systems: {len(world.systems())}")
print(f"planets: {len(world.planets())}")
print(f"civilizations: {len(world.civilizations())}")

simulation = world.simulation(SimulationConfig(validate_after_tick=True))
simulation.run(until=2000)

print(f"simulated time reached: {simulation.clock.current_time}")

for civilization in world.civilizations():
    controlled = world.controlled_systems(civilization)
    print(
        civilization.name,
        "spreading_power=%.3f" % world.spreading_power(civilization),
        "systems=%d" % len(controlled),
        "planets=%d" % len(world.controlled_planets(civilization)),
        "trade_routes=%d" % len(civilization.trade.active_routes()),
        "events=%d" % len(civilization.history.events),
    )

first_civilization = world.civilizations()[0]
origin_planet = world.origin_world(first_civilization)
print(f"origin world of {first_civilization.name}: {origin_planet.name}, habitability={origin_planet.habitability.base_score:.2f}")

details = world.details.for_planet(origin_planet)
print(f"derived population: {details.population}, cities: {len(details.cities)}")
for city in details.cities[:3]:
    print("  city:", city.name, "population=%d" % city.population)

sample_system = world.controlled_systems(first_civilization)[0]
traffic = world.details.traffic_for(sample_system)
print(f"traffic for {sample_system.name}: ships={traffic.estimated_ships}, congestion={traffic.congestion:.2f}")

breakpoint()
