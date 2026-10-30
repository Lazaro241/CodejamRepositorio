"""Solver protocol and shared run context for deterministic optimization."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Protocol

from planner.domain.models import Dataset, Plan
from planner.rules.base import RuleSet


@dataclass(slots=True)
class SolveContext:
    """Run-scoped seed, deadline and logger shared by solver stages."""

    seed: int = 0
    deadline: float | None = None
    rng: random.Random = field(init=False, repr=False)
    log: logging.Logger = field(default_factory=lambda: logging.getLogger("planner.solver"))

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)


class Solver(Protocol):
    """Strategy contract for an end-to-end dataset-to-plan solver."""

    def solve(self, ds: Dataset, rules: RuleSet, ctx: SolveContext) -> Plan:
        """Produce a plan using only the supplied dataset and run context."""
        ...


__all__ = ["SolveContext", "Solver"]
