"""First-improvement descent shared by all neighborhood strategies."""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence

from planner.solvers.improvement.base import Operator, Routes


class LocalSearch:
    """Improve route sets without coupling the loop to specific operators."""

    def __init__(
        self,
        operators: Sequence[Operator],
        evaluate: Callable[[Sequence[Sequence[int]]], int],
    ) -> None:
        self.operators = tuple(operators)
        self.evaluate = evaluate

    def improve(
        self,
        routes: Sequence[Sequence[int]],
        deadline: float | None = None,
    ) -> Routes:
        """Return a non-worsening local optimum or best route before deadline.

        `deadline` is an absolute `time.monotonic()` timestamp. Evaluation is
        injected so the search always uses the caller's authoritative cost.
        """
        best = [list(route) for route in routes]
        best_score = self.evaluate(best)
        if self._expired(deadline):
            return best

        while True:
            improved = False
            for operator in self.operators:
                for candidate in operator.neighbors(best):
                    if self._expired(deadline):
                        return best
                    candidate_score = self.evaluate(candidate)
                    if self._expired(deadline):
                        return best
                    if candidate_score < best_score:
                        best = [list(route) for route in candidate]
                        best_score = candidate_score
                        improved = True
                        break
                if improved:
                    break
            if not improved:
                return best

    def search(
        self,
        routes: Sequence[Sequence[int]],
        deadline: float | None = None,
    ) -> Routes:
        """Alias for `improve`, convenient for solver pipeline call sites."""
        return self.improve(routes, deadline)

    @staticmethod
    def _expired(deadline: float | None) -> bool:
        return deadline is not None and time.monotonic() >= deadline


__all__ = ["LocalSearch"]
