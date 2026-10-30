"""Sweep-angle clustering and route construction for delivery orders."""

from __future__ import annotations

from math import atan2
from typing import Protocol

from planner.domain.geometry import manhattan
from planner.domain.models import Dataset, Order
from planner.solvers.construction.nearest_neighbor import nearest_neighbor


class Constructor(Protocol):
    """Strategy contract for building one route per requested group."""

    def build(self, ds: Dataset, k: int, offset: int) -> list[list[int]]:
        """Build `k` balanced routes containing dataset order IDs."""
        ...


class SweepConstructor:
    """Cluster by polar angle, then order each group from the actual depot.

    The offset rotates the angularly sorted orders before splitting, enabling
    deterministic alternative partitions without changing the clustering rule.
    """

    def build(self, ds: Dataset, k: int, offset: int = 0) -> list[list[int]]:
        """Return exactly `k` balanced routes; surplus groups are empty."""
        if k < 1:
            raise ValueError("k debe ser al menos 1.")

        depot = ds.world.depot
        orders = sorted(ds.orders.values(), key=lambda order: self._sweep_key(order, depot))
        if orders:
            start = offset % len(orders)
            orders = orders[start:] + orders[:start]

        group_size, larger_group_count = divmod(len(orders), k)
        routes: list[list[int]] = []
        start = 0
        for group_index in range(k):
            size = group_size + (group_index < larger_group_count)
            group = orders[start : start + size]
            routes.append(nearest_neighbor(group, depot))
            start += size
        return routes

    @staticmethod
    def _sweep_key(order: Order, depot: tuple[int, int]) -> tuple[float, int, int]:
        """Sort by angle, then radius and ID to resolve collinear orders."""
        dx = order.x - depot[0]
        dy = order.y - depot[1]
        return atan2(dy, dx), manhattan(depot, (order.x, order.y)), order.id


__all__ = ["Constructor", "SweepConstructor"]
