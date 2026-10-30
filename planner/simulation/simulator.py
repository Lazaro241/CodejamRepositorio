"""Cost simulation, a line-by-line replica of the official simulator.

Source of truth: `../quickdrop-sim/quickdrop/simulador.py::simular` (see
docs/01-contexto.md). The parity tests in `tests/simulation/test_parity.py`
assert exactly the same totals the official `python -m quickdrop simular`
prints, so any drift here fails loudly.

Semantics kept identical: integer minutes throughout; travel time is
`blocks x minutes_per_block`; a delivery occupies the vehicle `service_time`
starting on arrival (the official "espera" column can only be 0 today, there
are no time windows yet); a literal `DEPOSITO` stop returns to the depot,
pays `load_time` and starts a new trip; the final (implicit) return to the
depot is counted in blocks and time. The makespan is `max over vehicles of
route end time - departure` (0 when no vehicle is used), and a vehicle is
"used" iff its route contains at least one non-`DEPOSITO` stop.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Protocol

from planner.domain.geometry import manhattan
from planner.domain.models import Dataset, Evaluation, Plan, Vehicle
from planner.simulation.objective import SimulationStats, default_objective
from planner.simulation.validator import DEPOSITO, validate_routes

if TYPE_CHECKING:

    class RuleLike(Protocol):
        """The slice of T4's `Rule` that `simulate` uses today.

        WHY duck-typed: `planner/rules/base.py` does not exist yet (T4 owns
        it), and `simulation` must not create `planner/rules/` files. Any
        iterable of objects with this `expand` shape is accepted; with the
        final design T4's `RuleSet`/`Rule` simply provides that shape
        (docs/03 lets `simulation` import `planner.rules` only later).
        """

        name: str

        def expand(
            self, vehicle: Vehicle, route: Sequence[int], ds: Dataset
        ) -> Sequence[int | str]: ...


def simulate(dataset: Dataset, plan: Plan, rules: Iterable[RuleLike] | None) -> Evaluation:
    """Official-parity evaluation of `plan` over `dataset` under `rules`.

    `rules` is intentionally duck-typed: `planner/rules/base.py` (T4) does not
    exist yet, so any iterable of objects exposing
    `expand(vehicle, route, dataset) -> stops` works, and `None` or an empty
    iterable means "no rules". Rules chain in order: each one transforms the
    route produced so far, mirroring how an ordered `RuleSet` applies its
    active rules.
    """
    expanded = _apply_rules(dataset, plan.routes, rules)
    errors = validate_routes(dataset, expanded)
    if errors:
        # Official behavior for an invalid plan: `Resultado(valido=False)` —
        # nothing is simulated, no cost is reported, the dataset scores 0.
        return Evaluation(total=0, breakdown={}, unserved=(), violations=tuple(errors))

    blocks = 0
    used_vehicles = 0
    finish = dataset.world.departure
    delivered: set[int] = set()
    for vehicle in dataset.vehicles:
        stops = expanded.get(vehicle.id, ())
        if not any(stop != DEPOSITO for stop in stops):
            # Official `continue`: a vehicle with no deliveries is not used and
            # contributes neither blocks nor time (a lone DEPOSITO stop means
            # nothing at all, exactly like the official main loop).
            continue
        used_vehicles += 1
        route_blocks, route_finish, route_delivered = _drive(dataset, stops)
        blocks += route_blocks
        finish = max(finish, route_finish)
        delivered.update(route_delivered)

    # Official `no_asignados`: dataset orders the plan never mentions, in
    # dataset order. Missing orders fail (cost per failure) but never invalidate.
    unserved = tuple(order_id for order_id in dataset.orders if order_id not in delivered)
    stats = SimulationStats(
        blocks=blocks,
        used_vehicles=used_vehicles,
        makespan=finish - dataset.world.departure,
        failures=len(unserved),
    )
    breakdown = default_objective().breakdown(stats, dataset.world)
    return Evaluation(
        total=sum(breakdown.values()),
        breakdown=breakdown,
        unserved=unserved,
        violations=(),
    )


def _apply_rules(
    dataset: Dataset,
    plan_routes: Mapping[str, Sequence[int | str]],
    rules: Iterable[RuleLike] | None,
) -> dict[str, tuple[int | str, ...]]:
    """Expand every planned route through the rule chain, plan order preserved.

    WHY plan order and why unknown vehicles survive here: `validate_routes`
    must number routes the way the official loop over `plan.rutas` does and
    must still report a route whose vehicle is unknown, so the expanded map
    mirrors `plan_routes` exactly (dataset vehicles get their rule-expanded
    stops; an unknown vehicle keeps its raw stops for the error report, since
    `expand` has no `Vehicle` to be called with).
    """
    chain: tuple[RuleLike, ...] = tuple(rules) if rules is not None else ()
    expanded: dict[str, tuple[int | str, ...]] = {}
    for vehicle_id, raw_route in plan_routes.items():
        vehicle = next((v for v in dataset.vehicles if v.id == vehicle_id), None)
        if vehicle is None:
            expanded[vehicle_id] = tuple(raw_route)
            continue
        route: tuple[int | str, ...] = tuple(raw_route)
        for rule in chain:
            route = tuple(rule.expand(vehicle, route, dataset))
        expanded[vehicle_id] = route
    return expanded


def _drive(dataset: Dataset, stops: Sequence[int | str]) -> tuple[int, int, set[int]]:
    """Simulate one used route: returns (blocks, finish time, delivered ids).

    Time math stays in integer minutes like the official simulator. Every
    remaining stop is an order id (validate_routes cleared anything else), so
    indexing `dataset.orders` is safe.
    """
    world = dataset.world
    position = world.depot
    clock = world.departure
    blocks = 0
    delivered: set[int] = set()
    for stop in stops:
        if stop == DEPOSITO:
            # RECARGA: back to the depot, pay the trip, then the load time; a
            # new trip starts from the depot afterwards.
            leg = manhattan(position, world.depot)
            blocks += leg
            clock += leg * world.minutes_per_block + world.load_time
            position = world.depot
            continue
        order = dataset.orders[stop]
        leg = manhattan(position, (order.x, order.y))
        blocks += leg
        clock += leg * world.minutes_per_block
        position = (order.x, order.y)
        clock += world.service_time  # ENTREGADO: occupied from arrival onwards
        delivered.add(stop)
    # REGRESO: the implicit final return is real distance and real time (the
    # official simulator adds both), but carries no load time.
    leg = manhattan(position, world.depot)
    blocks += leg
    clock += leg * world.minutes_per_block
    return blocks, clock, delivered


__all__ = ["simulate"]
