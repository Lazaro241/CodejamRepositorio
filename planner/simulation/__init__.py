"""Simulation layer: official-simulator replica, cost terms and validator.

Public surface per docs/03-arquitectura.md; this package is the single source
of truth for costs (`docs/AGENTS.md`) — solvers call `simulate`, never
reimplement it. It imports only stdlib + `planner.domain` (+ validator) and
stays duck-typed about rules until T4 formally lands `planner.rules`.
"""

from __future__ import annotations

from planner.simulation.objective import (
    DEFAULT_TERMS,
    BlocksCost,
    CompositeCost,
    CostTerm,
    FailureCost,
    MakespanCost,
    SimulationStats,
    VehicleCost,
    default_objective,
)
from planner.simulation.simulator import simulate
from planner.simulation.validator import DEPOSITO, validate, validate_routes

__all__ = [
    "DEFAULT_TERMS",
    "DEPOSITO",
    "BlocksCost",
    "CompositeCost",
    "CostTerm",
    "FailureCost",
    "MakespanCost",
    "SimulationStats",
    "VehicleCost",
    "default_objective",
    "simulate",
    "validate",
    "validate_routes",
]
