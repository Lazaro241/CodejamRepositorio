"""Validator unit tests: the four official invalidities, nothing else invalid.

Per official spec §5 these are the ONLY invalid conditions; a missing order
must NOT appear here (it fails instead, `test_simulator.py` covers that).
"""

from __future__ import annotations

from planner.domain.models import Dataset, Order, Plan, Vehicle, World
from planner.simulation import validate

_WORLD = World(
    width=20,
    height=20,
    depot=(0, 0),
    departure=480,
    service_time=5,
    load_time=10,
    minutes_per_block=3,
    cost_per_block=3,
    cost_per_vehicle=60,
    cost_per_minute=1,
    cost_per_failure=200,
)


def _dataset() -> Dataset:
    orders = [Order(1, 5, 5, 1), Order(2, 7, 3, 1), Order(3, 10, 10, 1)]
    return Dataset(world=_WORLD, orders={o.id: o for o in orders}, vehicles=(Vehicle("V1"),))


def test_valid_plan_with_recharge_has_no_violations() -> None:
    plan = Plan({"V1": (1, 2, "DEPOSITO", 3)})
    assert validate(_dataset(), plan) == []


def test_empty_and_absent_vehicles_are_fine() -> None:
    dataset = _dataset()
    assert validate(dataset, Plan({})) == []  # missing orders fail, not invalidate
    assert validate(dataset, Plan({"V2": (1,)})) == ["Ruta 1: el vehículo 'V2' no existe."]


def test_unknown_order_violates() -> None:
    plan = Plan({"V1": (1, 99)})
    assert validate(_dataset(), plan) == ["Vehículo V1: el pedido 99 no existe."]


def test_repeated_order_cross_vehicles_violates() -> None:
    dataset = _dataset()
    dataset = Dataset(
        world=dataset.world, orders=dataset.orders, vehicles=(*dataset.vehicles, Vehicle("V2"))
    )
    plan = Plan({"V1": (1,), "V2": (2, 1)})
    assert validate(dataset, plan) == ["El pedido 1 aparece más de una vez (vehículos V1 y V2)."]


def test_errors_number_routes_in_plan_order_and_skip_unknown_vehicle_stops() -> None:
    # Official loop: a route with an unknown/repeated vehicle is skipped, its
    # stops are not further inspected.
    dataset = _dataset()
    plan = Plan({"V9": (1, 2), "V1": (3, 3)})
    assert validate(dataset, plan) == [
        "Ruta 1: el vehículo 'V9' no existe.",
        "El pedido 3 aparece más de una vez (vehículos V1 y V1).",
    ]
