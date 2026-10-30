"""Correctness tests for `planner.domain.geometry.manhattan`."""

from __future__ import annotations

from planner.domain.geometry import manhattan


class TestManhattan:
    def test_basic(self) -> None:
        assert manhattan((0, 0), (3, 4)) == 7

    def test_symmetric(self) -> None:
        assert manhattan((3, 4), (0, 0)) == manhattan((0, 0), (3, 4))

    def test_zero_distance(self) -> None:
        assert manhattan((5, 5), (5, 5)) == 0

    def test_axis_aligned(self) -> None:
        assert manhattan((2, 9), (2, 1)) == 8

    def test_negative_coordinates(self) -> None:
        assert manhattan((-3, -2), (1, 1)) == 7

    def test_returns_int(self) -> None:
        assert isinstance(manhattan((0, 0), (1, 1)), int)

    def test_across_axises_sums_not_diagonal(self) -> None:
        # Diagonal would be Chebyshev (2); taxicab must sum both deltas.
        assert manhattan((0, 0), (3, 3)) == 6
