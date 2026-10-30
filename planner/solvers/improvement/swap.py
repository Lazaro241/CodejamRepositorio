"""Swap moves between order positions within or across routes."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from planner.solvers.improvement.base import Routes


class Swap:
    """Exchange every pair of distinct order positions."""

    def neighbors(self, routes: Sequence[Sequence[int]]) -> Iterator[Routes]:
        """Yield swap candidates while preserving all orders and route sizes."""
        original = [list(route) for route in routes]
        for left_route, route in enumerate(original):
            for left_index in range(len(route)):
                for right_route in range(left_route, len(original)):
                    right_start = left_index + 1 if right_route == left_route else 0
                    for right_index in range(right_start, len(original[right_route])):
                        candidate = [list(current) for current in original]
                        candidate[left_route][left_index], candidate[right_route][right_index] = (
                            candidate[right_route][right_index],
                            candidate[left_route][left_index],
                        )
                        yield candidate


__all__ = ["Swap"]
