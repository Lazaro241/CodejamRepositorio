"""Shared route types and neighborhood strategy contract."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import Protocol, TypeAlias

Routes: TypeAlias = list[list[int]]


class Operator(Protocol):
    """Produce candidate route collections without mutating the input."""

    def neighbors(self, routes: Sequence[Sequence[int]]) -> Iterator[Routes]:
        """Yield one neighboring solution at a time."""
        ...


__all__ = ["Operator", "Routes"]
