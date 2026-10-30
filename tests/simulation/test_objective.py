"""Unit tests: cost terms compose additively (docs/05-test rule `sum == total`).

The breakdown of the official simulator's four lines must sum to `total` on
every shape of plan we simulate; breaking that invariant breaks the CLI report
and every parity test at once, so it is asserted directly here with
hand-built worlds and plans (no fixture files needed).
"""

from __future__ import annotations

from planner.domain.models import Dataset, Order, Plan, Vehicle, World
from planner.simulation.objective import (
    DEFAULT_TERMS,
    CompositeCost,
    SimulationStats,
    default_objective,
)
from planner.simulation.simulator import simulate


def _world(**overrides: int) -> World:
    values: dict[str, int] = {
        "width": 20,
        "height": 20,
        "service_time": 5,
        "load_time": 10,
        "minutes_per_block": 3,
        "cost_per_block": 3,
        "cost_per_vehicle": 60,
        "cost_per_minute": 1,
        "cost_per_failure": 200,
    }
    values.update(overrides)
    return World(
        width=values["width"],
        height=values["height"],
        depot=(0, 0),
        departure=480,
        service_time=values["service_time"],
        load_time=values["load_time"],
        minutes_per_block=values["minutes_per_block"],
        cost_per_block=values["cost_per_block"],
        cost_per_vehicle=values["cost_per_vehicle"],
        cost_per_minute=values["cost_per_minute"],
        cost_per_failure=values["cost_per_failure"],
    )


def _dataset(world: World, orders: list[Order], vehicles: list[str]) -> Dataset:
    return Dataset(
        world=world,
        orders={order.id: order for order in orders},
        vehicles=tuple(Vehicle(id) for id in vehicles),
    )


def test_default_terms_are_exactly_the_official_four() -> None:
    names = [term.name for term in DEFAULT_TERMS]
    assert names == ["distancia", "vehiculos", "tiempo", "fallas"]


def test_terms_are_stateless_and_compose() -> None:
    stats = SimulationStats(blocks=100, used_vehicles=2, makespan=300, failures=1)
    composite = default_objective()
    world = _world()
    breakdown = composite.breakdown(stats, world)
    assert breakdown == {"distancia": 300, "vehiculos": 120, "tiempo": 300, "fallas": 200}
    assert sum(breakdown.values()) == composite.total(stats, world)


def test_terms_scale_with_world_costs() -> None:
    stats = SimulationStats(blocks=10, used_vehicles=1, makespan=10, failures=0)
    world = _world(cost_per_block=7, cost_per_vehicle=11, cost_per_minute=2)
    assert default_objective().total(stats, world) == 70 + 11 + 20


def test_composite_accepts_a_custom_term() -> None:
    class Surcharge:
        name = "sobrecargo"

        def cost(self, stats: SimulationStats, world: World) -> int:
            return 50

    composite = CompositeCost([*DEFAULT_TERMS, Surcharge()])
    stats = SimulationStats(0, 0, 0, 0)
    assert composite.total(stats, _world()) == 50


def test_breakdown_sums_to_total_through_simulate_all_failures() -> None:
    world = _world()
    dataset = _dataset(world, [Order(1, 5, 5, 3)], ["V1"])
    evaluation = simulate(dataset, Plan({}), rules=None)
    assert evaluation.violations == ()
    assert evaluation.unserved == (1,)
    assert evaluation.breakdown == {
        "distancia": 0,
        "vehiculos": 0,
        "tiempo": 0,
        "fallas": 200,
    }
    assert sum(evaluation.breakdown.values()) == evaluation.total == 200


def test_breakdown_sums_to_total_through_simulate_reload_plan() -> None:
    world = _world()
    orders = [Order(1, 4, 0, 1), Order(2, 10, 0, 1), Order(3, 10, 0, 1)]
    dataset = _dataset(world, orders, ["V1"])
    plan = Plan({"V1": (1, 2, "DEPOSITO", 3)})
    evaluation = simulate(dataset, plan, rules=None)
    # 4 + 6 + 10 (recarga) + 10 + 10 (regreso) = 40 blocks; one used vehicle;
    # final time 625 => makespan 625 - 480 = 145.
    assert evaluation.breakdown == {
        "distancia": 120,
        "vehiculos": 60,
        "tiempo": 145,
        "fallas": 0,
    }
    assert sum(evaluation.breakdown.values()) == evaluation.total
