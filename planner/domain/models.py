"""Immutable domain models for the QuickDrop planner.

Why immutable: a `Dataset`/`Plan` is shared across io, rules, solvers and
simulation; freezing the dataclasses makes it impossible for one layer to
accidentally mutate data owned by another, and lets helpers like
`MappingProxyType` keep even the mappings read-only. `extra` captures unknown
dataset fields so io stays forward-compatible with new event fields without
changing these models.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

# Choice: `extra` defaults to a plain `{}` via default_factory. A module-level
# `MappingProxyType({})` default is rejected by dataclasses (mappingproxy is
# unhashable), and keeping it simple beats a sentinel hack across 4 classes.
# Read-only behavior comes from the `Mapping[str, Any]` hint and the frozen
# contract: io passes extra data in and must never mutate it afterwards.


@dataclass(frozen=True, slots=True)
class World:
    """Static rules of the delivery day, read verbatim from the dataset.

    Everything is data-driven (AGENTS.md forbids hardcoding world values) so the
    planner adapts to hidden datasets whose grid, costs and times may differ.
    `departure` is in minutes since midnight (08:00 -> 480) to keep time math
    integer-only and deterministic.
    """

    width: int
    height: int
    depot: tuple[int, int]
    departure: int  # minutes (08:00 -> 480)
    service_time: int
    load_time: int
    minutes_per_block: int
    cost_per_block: int
    cost_per_vehicle: int
    cost_per_minute: int
    cost_per_failure: int
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Order:
    """A delivery request located at (x, y).

    `weight` is 0 when the dataset omits/nulls it (weight constrains nothing
    today, but it is preserved because future rules will use it).
    """

    id: int
    x: int
    y: int
    weight: int
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Vehicle:
    """A delivery vehicle.

    Today vehicles carry only an id (no capacity in the dataset); `extra` holds
    any unknown fields so upcoming event rules can read them without a model
    change.
    """

    id: str
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Dataset:
    """The parsed input: a `World` plus every order and vehicle.

    Orders are keyed by `Order.id` (ids may be non-consecutive) and vehicles are
    a tuple in dataset order, which defines the solver's route order.
    """

    world: World
    orders: Mapping[int, Order]
    vehicles: tuple[Vehicle, ...]


@dataclass(frozen=True, slots=True)
class Plan:
    """The solver's output: routes per vehicle id.

    Stops are order ids or the literal "DEPOSITO"; keeping "DEPOSITO" as a plain
    string (not an enum) mirrors what `io` writes and what the simulator reads.
    """

    routes: Mapping[str, tuple[int | str, ...]]


@dataclass(frozen=True, slots=True)
class Evaluation:
    """Outcome of simulating a plan under the active rules.

    `breakdown` maps cost-term names to amounts so the high total stays
    explainable; `unserved`/`violations` keep failures first-class because an
    invalid plan scores 0 and must be visible, not hidden.
    """

    total: int
    breakdown: Mapping[str, int]
    unserved: tuple[int, ...]
    violations: tuple[str, ...]
