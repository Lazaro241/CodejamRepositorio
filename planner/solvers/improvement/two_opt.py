"""2-opt reversals within a route, a deterministic route improvement move."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from planner.solvers.improvement.base import Routes


class TwoOpt:
    """Generate every contiguous segment reversal in each route."""

    def neighbors(self, routes: Sequence[Sequence[int]]) -> Iterator[Routes]:
        """Yield each 2-opt route set without changing `routes`."""
        original = [list(route) for route in routes]
        for route_index, route in enumerate(original):
            for start in range(len(route) - 1):
                for end in range(start + 1, len(route)):
                    candidate = [list(current) for current in original]
                    candidate[route_index][start : end + 1] = reversed(
                        candidate[route_index][start : end + 1]
                    )
                    yield candidate


__all__ = ["TwoOpt"]
