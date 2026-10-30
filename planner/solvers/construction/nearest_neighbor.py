"""Nearest-neighbor ordering for one group of deliveries."""

from __future__ import annotations

from collections.abc import Sequence

from planner.domain.geometry import manhattan
from planner.domain.models import Order


def nearest_neighbor(group: Sequence[Order], depot: tuple[int, int]) -> list[int]:
    """Return order IDs by repeatedly visiting the closest remaining order.

    Ties are broken by order ID so route generation remains deterministic.
    The first leg starts at the supplied dataset depot, never a fixed origin.
    """
    remaining = list(enumerate(group))
    position = depot
    route: list[int] = []

    while remaining:
        candidate_index, order = min(
            remaining,
            key=lambda candidate: (
                manhattan(position, (candidate[1].x, candidate[1].y)),
                candidate[1].id,
                candidate[0],
            ),
        )
        route.append(order.id)
        position = (order.x, order.y)
        remaining = [candidate for candidate in remaining if candidate[0] != candidate_index]

    return route


__all__ = ["nearest_neighbor"]
