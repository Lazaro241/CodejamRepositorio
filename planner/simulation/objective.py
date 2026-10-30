"""Composable cost terms (Composite, docs/04-patrones.md).

Why a Composite instead of one hardcoded formula: every event brings new cost
terms (rule terms, future vehicle fields) and the breakdown printed by the CLI
must stay additive and explainable. `CostTerm` protocols, `DEFAULT_TERMS`
replicates the official simulator's line-by-line cost:

    costo = costo_por_cuadra · cuadras + costo fijo · usados
          + costo_por_minuto_total · makespan + costo_por_falla · fallas

using the official report names ("distancia", "vehiculos", "tiempo",
"fallas") as term names, so `sum(breakdown.values()) == total` line by line.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Protocol

from planner.domain.models import World


@dataclass(frozen=True, slots=True)
class SimulationStats:
    """Raw simulation magnitudes the cost terms are computed from.

    All integers, straight out of `simulator.py`; keeping them as one value
    object is what makes a term stateless and testable on its own.
    """

    blocks: int
    used_vehicles: int
    makespan: int
    failures: int


class CostTerm(Protocol):
    """One line of the cost breakdown.

    WHY a Protocol per term instead of the stats being passed to `simulate`
    directly: a new event rule adds its cost as one more term (T4) without
    editing `simulator.py`. `name` must match what the official report calls
    the line when the term replicates one of its lines.
    """

    name: str

    def cost(self, stats: SimulationStats, world: World) -> int: ...


@dataclass(frozen=True, slots=True)
class BlocksCost:
    """`costo_por_cuadra` per block travelled, all vehicles, incl. final returns."""

    name: ClassVar[str] = "distancia"

    def cost(self, stats: SimulationStats, world: World) -> int:
        return stats.blocks * world.cost_per_block


@dataclass(frozen=True, slots=True)
class VehicleCost:
    """Fixed cost per used vehicle (>= 1 delivery in its routes).

    WHY `world.cost_per_vehicle` and not a per-vehicle amount: the official
    loader sets every vehicle's `costo_fijo` to `por_vehiculo` at load time, so
    multiplying by the used count is exactly equivalent with today's format.
    """

    name: ClassVar[str] = "vehiculos"

    def cost(self, stats: SimulationStats, world: World) -> int:
        return stats.used_vehicles * world.cost_per_vehicle


@dataclass(frozen=True, slots=True)
class MakespanCost:
    """`costo_por_minuto_total` per minute until the last vehicle is back."""

    name: ClassVar[str] = "tiempo"

    def cost(self, stats: SimulationStats, world: World) -> int:
        return stats.makespan * world.cost_per_minute


@dataclass(frozen=True, slots=True)
class FailureCost:
    """`costo_por_falla` per unserved order; a missing order fails, never
    invalidates."""

    name: ClassVar[str] = "fallas"

    def cost(self, stats: SimulationStats, world: World) -> int:
        return stats.failures * world.cost_per_failure


#: The official simulator's four lines, in its report order. New rules append
#: their terms when T4 registers them; existing ones must never be reordered
#: (the breakdown maps are compared in parity tests).
DEFAULT_TERMS: tuple[CostTerm, ...] = (
    BlocksCost(),
    VehicleCost(),
    MakespanCost(),
    FailureCost(),
)


@dataclass(frozen=True, slots=True)
class CompositeCost:
    """Composite of cost terms (docs/04): the single place costs get summed."""

    terms: Sequence[CostTerm]

    def breakdown(self, stats: SimulationStats, world: World) -> dict[str, int]:
        """Line name -> amount; duplicate names would silently overwrite, so the
        first term wins and keeps the map length == len(terms)."""
        breakdown: dict[str, int] = {}
        for term in self.terms:
            breakdown.setdefault(term.name, term.cost(stats, world))
        return breakdown

    def total(self, stats: SimulationStats, world: World) -> int:
        # Same summation the official simulator does over its componentes dict.
        return sum(self.breakdown(stats, world).values())


def default_objective() -> CompositeCost:
    """The cost structure of the official simulator: exactly its four lines."""
    return CompositeCost(DEFAULT_TERMS)


__all__ = [
    "DEFAULT_TERMS",
    "BlocksCost",
    "CompositeCost",
    "CostTerm",
    "FailureCost",
    "MakespanCost",
    "SimulationStats",
    "VehicleCost",
    "default_objective",
]
