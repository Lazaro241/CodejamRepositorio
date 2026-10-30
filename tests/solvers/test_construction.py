"""Construction tests for depot-aware sweep and nearest-neighbor routes."""

from __future__ import annotations

from planner.domain.models import Dataset, Order, Vehicle, World
from planner.solvers.construction import SweepConstructor, nearest_neighbor


def _dataset(orders: list[Order], depot: tuple[int, int]) -> Dataset:
    world = World(
        width=30,
        height=30,
        depot=depot,
        departure=480,
        service_time=5,
        load_time=10,
        minutes_per_block=3,
        cost_per_block=3,
        cost_per_vehicle=60,
        cost_per_minute=1,
        cost_per_failure=200,
    )
    return Dataset(world, {order.id: order for order in orders}, (Vehicle("V1"),))


def test_nearest_neighbor_starts_at_depot_and_visits_closest_next() -> None:
    orders = [Order(1, 0, 0, 1), Order(2, 11, 10, 1), Order(3, 10, 13, 1)]

    assert nearest_neighbor(orders, (10, 10)) == [2, 3, 1]


def test_sweep_builds_balanced_unique_routes_around_dataset_depot() -> None:
    orders = [
        Order(1, 12, 10, 1),
        Order(2, 11, 13, 1),
        Order(3, 7, 12, 1),
        Order(4, 8, 8, 1),
        Order(5, 13, 7, 1),
    ]
    routes = SweepConstructor().build(_dataset(orders, (10, 10)), k=2, offset=0)
    flattened = [order_id for route in routes for order_id in route]
    orders_by_id = {order.id: order for order in orders}

    assert len(routes) == 2
    assert sorted(map(len, routes)) == [2, 3]
    assert sorted(flattened) == [1, 2, 3, 4, 5]
    assert len(flattened) == len(set(flattened))
    assert all(
        route[0]
        == min(
            route,
            key=lambda order_id: (
                abs(orders_by_id[order_id].x - 10) + abs(orders_by_id[order_id].y - 10)
            ),
        )
        for route in routes
    )


def test_offset_rotates_angular_start_before_balanced_split() -> None:
    orders = [
        Order(1, 12, 10, 1),
        Order(2, 11, 12, 1),
        Order(3, 8, 12, 1),
        Order(4, 8, 8, 1),
        Order(5, 12, 8, 1),
    ]
    dataset = _dataset(orders, (10, 10))
    constructor = SweepConstructor()

    first_partition = {frozenset(route) for route in constructor.build(dataset, k=2, offset=0)}
    rotated_partition = {frozenset(route) for route in constructor.build(dataset, k=2, offset=1)}

    assert first_partition != rotated_partition


def test_single_order_and_more_groups_than_orders() -> None:
    constructor = SweepConstructor()
    dataset = _dataset([Order(42, 11, 10, 1)], (10, 10))

    assert constructor.build(dataset, k=1, offset=0) == [[42]]

    dataset = _dataset([Order(7, 11, 10, 1), Order(9, 10, 11, 1)], (10, 10))
    routes = constructor.build(dataset, k=4, offset=0)
    assert len(routes) == 4
    assert sorted(order_id for route in routes for order_id in route) == [7, 9]
    assert sum(not route for route in routes) == 2
