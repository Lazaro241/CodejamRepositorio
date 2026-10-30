"""Construction and immutability tests for `planner.domain.models`."""

from __future__ import annotations

import dataclasses

import pytest

from planner.domain.models import Dataset, Evaluation, Order, Plan, Vehicle, World


def make_world(**overrides: int) -> World:
    """Return a complete `World` (nothing hardcoded: values live in tests only)."""
    fields: dict[str, int | tuple[int, int]] = {
        "width": 20,
        "height": 30,
        "depot": (0, 0),
        "departure": 480,  # 08:00
        "service_time": 3,
        "load_time": 5,
        "minutes_per_block": 2,
        "cost_per_block": 10,
        "cost_per_vehicle": 100,
        "cost_per_minute": 1,
        "cost_per_failure": 1000,
    }
    return World(**fields | overrides)  # type: ignore[arg-type]


def make_dataset() -> Dataset:
    return Dataset(
        world=make_world(),
        orders={1: Order(id=1, x=2, y=3, weight=4)},
        vehicles=(Vehicle(id="V1"), Vehicle(id="V2")),
    )


class TestWorld:
    def test_full_construction(self) -> None:
        world = make_world()
        assert (world.width, world.height) == (20, 30)
        assert world.depot == (0, 0)
        assert world.departure == 480

    def test_mapping_extra_is_stored(self) -> None:
        world = make_world(extra={"ventana": 60})
        assert world.extra["ventana"] == 60

    def test_immutable(self) -> None:
        world = make_world()
        with pytest.raises(dataclasses.FrozenInstanceError):
            world.width = 1  # type: ignore[misc]


class TestOrder:
    def test_weight_is_int(self) -> None:
        order = Order(id=7, x=5, y=6, weight=2)
        assert order.weight == 2
        assert isinstance(order.weight, int)

    def test_immutable(self) -> None:
        order = Order(id=7, x=5, y=6, weight=0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            order.id = 8  # type: ignore[misc]


class TestVehicle:
    def test_only_id(self) -> None:
        vehicle = Vehicle(id="V1")
        assert vehicle.id == "V1"
        assert vehicle.extra == {}

    def test_immutable(self) -> None:
        vehicle = Vehicle(id="V1")
        with pytest.raises(dataclasses.FrozenInstanceError):
            vehicle.id = "V2"  # type: ignore[misc]


class TestDataset:
    def test_order_keys_are_order_ids(self) -> None:
        orders = {
            3: Order(id=3, x=0, y=1, weight=1),
            8: Order(id=8, x=1, y=0, weight=1),  # non-consecutive ids allowed
        }
        dataset = Dataset(world=make_world(), orders=orders, vehicles=(Vehicle(id="A"),))
        assert set(dataset.orders) == {3, 8}
        assert dataset.orders[8].id == 8

    def test_immutable(self) -> None:
        dataset = make_dataset()
        with pytest.raises(dataclasses.FrozenInstanceError):
            dataset.world = None  # type: ignore[assignment]


class TestPlan:
    def test_routes_use_deposito_literal(self) -> None:
        plan = Plan(routes={"V1": ("DEPOSITO", 1, 2, "DEPOSITO")})
        stops = plan.routes["V1"]
        assert isinstance(stops, tuple)
        assert "DEPOSITO" in stops

    def test_immutable(self) -> None:
        plan = Plan(routes={})
        with pytest.raises(dataclasses.FrozenInstanceError):
            plan.routes = {"V1": ()}  # type: ignore[misc]


class TestEvaluation:
    def test_construction(self) -> None:
        outcome = Evaluation(
            total=42,
            breakdown={"blocks": 30, "vehicles": 12},
            unserved=(1,),
            violations=("pedido 1 repetido",),
        )
        assert outcome.total == 42
        assert outcome.unserved == (1,)

    def test_immutable(self) -> None:
        outcome = Evaluation(total=0, breakdown={}, unserved=(), violations=())
        with pytest.raises(dataclasses.FrozenInstanceError):
            outcome.total = 1  # type: ignore[misc]
