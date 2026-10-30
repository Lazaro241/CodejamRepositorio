"""Relocation moves that move one order within or between routes."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from planner.solvers.improvement.base import Routes


class Relocate:
    """Move each order to every insertion position, including other routes."""

    def neighbors(self, routes: Sequence[Sequence[int]]) -> Iterator[Routes]:
        """Yield non-identical relocation candidates without mutating input."""
        original = [list(route) for route in routes]
        for source_index, source in enumerate(original):
            for order_index in range(len(source)):
                for target_index, target in enumerate(original):
                    target_length = len(target) - (source_index == target_index)
                    for insert_index in range(target_length + 1):
                        candidate = [list(route) for route in original]
                        order_id = candidate[source_index].pop(order_index)
                        candidate[target_index].insert(insert_index, order_id)
                        if candidate != original:
                            yield candidate


__all__ = ["Relocate"]
