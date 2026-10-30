"""Tests for route neighborhoods and generic first-improvement search."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from planner.solvers.improvement import LocalSearch, Relocate, Swap, TwoOpt
from planner.solvers.improvement.base import Routes


def _assert_valid_neighbors(operator: object, routes: Routes) -> list[Routes]:
    neighbors = list(operator.neighbors(routes))  # type: ignore[attr-defined]
    expected_orders = sorted(order_id for route in routes for order_id in route)
    for candidate in neighbors:
        assert sorted(order_id for route in candidate for order_id in route) == expected_orders
        assert candidate != routes
    assert routes == [[1, 2, 3], [4, 5]]
    return neighbors


def test_two_opt_reverses_segments_and_preserves_input() -> None:
    routes = [[1, 2, 3], [4, 5]]
    neighbors = _assert_valid_neighbors(TwoOpt(), routes)

    assert [2, 1, 3] in [candidate[0] for candidate in neighbors]
    assert [3, 2, 1] in [candidate[0] for candidate in neighbors]


def test_relocate_moves_orders_within_and_between_routes() -> None:
    routes = [[1, 2, 3], [4, 5]]
    neighbors = _assert_valid_neighbors(Relocate(), routes)

    assert [[2, 1, 3], [4, 5]] in neighbors
    assert [[2, 3], [4, 5, 1]] in neighbors


def test_swap_exchanges_orders_within_and_between_routes() -> None:
    routes = [[1, 2, 3], [4, 5]]
    neighbors = _assert_valid_neighbors(Swap(), routes)

    assert [[2, 1, 3], [4, 5]] in neighbors
    assert [[4, 2, 3], [1, 5]] in neighbors


def test_operators_handle_empty_and_single_order_routes() -> None:
    routes = [[], [9], []]
    assert list(TwoOpt().neighbors(routes)) == []
    assert list(Swap().neighbors(routes)) == []
    relocated = list(Relocate().neighbors(routes))
    assert relocated == [[[9], [], []], [[], [], [9]]]


def test_local_search_never_worsens_and_accepts_new_operator_strategy() -> None:
    class ReverseOrders:
        """A new strategy proves LocalSearch does not branch on operator type."""

        def neighbors(self, routes: Sequence[Sequence[int]]) -> Iterator[Routes]:
            yield [list(reversed(route)) for route in routes]

    def evaluate(routes: Sequence[Sequence[int]]) -> int:
        return sum(
            abs(value - (index + 1)) for route in routes for index, value in enumerate(route)
        )

    initial = [[3, 2, 1]]
    improved = LocalSearch([ReverseOrders()], evaluate).improve(initial)

    assert improved == [[1, 2, 3]]
    assert evaluate(improved) <= evaluate(initial)
    assert initial == [[3, 2, 1]]


def test_local_search_respects_expired_deadline() -> None:
    evaluated: list[Routes] = []

    def evaluate(routes: Sequence[Sequence[int]]) -> int:
        evaluated.append([list(route) for route in routes])
        return sum(routes[0])

    initial = [[3, 1, 2]]
    result = LocalSearch([TwoOpt()], evaluate).improve(initial, deadline=0.0)

    assert result == initial
    assert evaluated == [initial]


def test_local_search_uses_strict_first_improvement() -> None:
    seen: list[Routes] = []

    class Candidates:
        def neighbors(self, routes: Sequence[Sequence[int]]) -> Iterator[Routes]:
            yield [[2, 1]]
            yield [[1, 2]]

    def evaluate(routes: Sequence[Sequence[int]]) -> int:
        seen.append([list(route) for route in routes])
        return 0 if routes == [[2, 1]] else 1

    result = LocalSearch([Candidates()], evaluate).improve([[1, 2]])

    assert result == [[2, 1]]
    assert seen == [[[1, 2]], [[2, 1]], [[2, 1]], [[1, 2]]]
