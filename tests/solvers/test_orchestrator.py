"""Orchestration tests for vehicle-count search and active rules."""

from __future__ import annotations

import logging

from planner.domain.models import Dataset, Order, Plan, Vehicle, World
from planner.rules.base import Rule, RuleSet
from planner.simulation import simulate, validate
from planner.solvers.base import SolveContext
from planner.solvers.orchestrator import Orchestrator


def _dataset(
    orders: list[Order], *, vehicle_cost: int, minute_cost: int, vehicle_count: int = 2
) -> Dataset:
    world = World(
        width=30,
        height=30,
        depot=(10, 10),
        departure=480,
        service_time=5,
        load_time=10,
        minutes_per_block=3,
        cost_per_block=0,
        cost_per_vehicle=vehicle_cost,
        cost_per_minute=minute_cost,
        cost_per_failure=100,
    )
    return Dataset(
        world,
        {order.id: order for order in orders},
        tuple(Vehicle(f"V{index + 1}") for index in range(vehicle_count)),
    )


def test_vehicle_cost_dominates_and_orchestrator_uses_one_vehicle() -> None:
    dataset = _dataset(
        [Order(1, 11, 10, 1), Order(2, 10, 11, 1)], vehicle_cost=1_000_000, minute_cost=0
    )

    plan = Orchestrator().solve(dataset, RuleSet(), SolveContext())

    assert len(plan.routes) == 1
    assert validate(dataset, plan) == []


def test_high_makespan_cost_prefers_parallel_vehicle_routes() -> None:
    dataset = _dataset([Order(1, 10, 10, 1), Order(2, 10, 10, 1)], vehicle_cost=0, minute_cost=100)

    plan = Orchestrator().solve(dataset, RuleSet(), SolveContext())

    assert len(plan.routes) == 2
    assert (
        simulate(dataset, plan, RuleSet()).total
        < simulate(dataset, Plan({"V1": (1, 2)}), RuleSet()).total
    )
    assert validate(dataset, plan) == []


def test_unassignable_orders_are_left_out_but_plan_stays_valid() -> None:
    class RejectOne(Rule):
        name = "reject_one"

        def assignable(self, order: Order, ds: Dataset) -> bool:
            return order.id != 2

    dataset = _dataset([Order(1, 11, 10, 1), Order(2, 10, 11, 1)], vehicle_cost=0, minute_cost=0)

    plan = Orchestrator().solve(dataset, RuleSet((RejectOne(),)), SolveContext())

    assert [stop for route in plan.routes.values() for stop in route] == [1]
    assert validate(dataset, plan) == []
    assert simulate(dataset, plan, RuleSet((RejectOne(),))).unserved == (2,)


def test_orchestrator_logs_cost_for_each_explored_k(caplog) -> None:
    dataset = _dataset([Order(1, 11, 10, 1), Order(2, 10, 11, 1)], vehicle_cost=0, minute_cost=0)

    with caplog.at_level(logging.INFO, logger="planner.solver"):
        Orchestrator().solve(dataset, RuleSet(), SolveContext())

    assert "k=1 costo=" in caplog.text
    assert "k=2 costo=" in caplog.text
