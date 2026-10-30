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

Rules (T4) plug in via `planner.rules.base.RuleSet`: chain expansion of the
planned routes, per-vehicle feasibility checks and per-rule extra cost lines.
With no active rule every result equals the pre-rules simulator exactly.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from planner.domain.geometry import manhattan
from planner.domain.models import Dataset, Evaluation, Plan
from planner.rules.base import Rule, RuleSet, as_ruleset
from planner.simulation.objective import SimulationStats, default_objective
from planner.simulation.validator import DEPOSITO, validate_routes


def simulate(dataset: Dataset, plan: Plan, rules: RuleSet | Iterable[Rule] | None) -> Evaluation:
    """Official-parity evaluation of `plan` over `dataset` under `rules`.

    `rules` is a `RuleSet` (preferred since T4) or, for T3 callers, `None` / an
    iterable of `Rule` objects — normalized by `as_ruleset`. With no active
    rule the evaluation is identical to the pre-rules simulator: routes intact
    and only the four official cost lines. Active rules chain in order: each
    one transforms the route produced so far (expand), reports feasibility
    violations into `Evaluation.violations` per used vehicle (check), and
    appends its own labeled term to the breakdown after the official lines
    (extra_cost; the line exists only when the rule charges — an active but
    costless rule never alters the evaluation). A rule violation is
    informative (ride along the cost, no
    invalidation): scoring the whole dataset 0 remains `validator`'s job,
    exactly like the official simulator.
    """
    ruleset = as_ruleset(rules)
    expanded = _apply_rules(dataset, plan.routes, ruleset)
    errors = validate_routes(dataset, expanded)
    if errors:
        # Official behavior for an invalid plan: `Resultado(valido=False)` —
        # nothing is simulated, no cost is reported, the dataset scores 0.
        # Rule checks do not even run: nothing about an invalid plan counts.
        return Evaluation(total=0, breakdown={}, unserved=(), violations=tuple(errors))

    blocks = 0
    used_vehicles = 0
    finish = dataset.world.departure
    delivered: set[int] = set()
    rule_violations: list[str] = []
    for vehicle in dataset.vehicles:
        stops = expanded.get(vehicle.id, ())
        if not any(stop != DEPOSITO for stop in stops):
            # Official `continue`: a vehicle with no deliveries is not used and
            # contributes neither blocks nor time (a lone DEPOSITO stop means
            # nothing at all, exactly like the official main loop). The rule
            # checks only ride along on routes that are actually driven.
            continue
        used_vehicles += 1
        route_blocks, route_finish, route_delivered = _drive(dataset, stops)
        blocks += route_blocks
        finish = max(finish, route_finish)
        delivered.update(route_delivered)
        rule_violations.extend(ruleset.check(vehicle, stops, dataset))

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
    base_evaluation = Evaluation(
        total=sum(breakdown.values()),
        breakdown=breakdown,
        unserved=unserved,
        violations=(),
    )

    rule_terms = ruleset.extra_breakdown(base_evaluation, dataset)
    # Only charging rules appear in the breakdown (amount != 0): with a
    # costless active rule the evaluation stays byte-identical to a run
    # without rules, and a rule line that charges nothing would be noise.
    if (
        not (charging := {name: amount for name, amount in rule_terms.items() if amount})
        and not rule_violations
    ):
        return base_evaluation
    merged_breakdown = dict(breakdown)
    for rule_name, amount in charging.items():
        # Sum on collision instead of overwrite: the invariant
        # `sum(breakdown.values()) == total` must hold for every evaluation.
        merged_breakdown[rule_name] = merged_breakdown.get(rule_name, 0) + amount
    return Evaluation(
        total=sum(merged_breakdown.values()),
        breakdown=merged_breakdown,
        unserved=unserved,
        violations=tuple(rule_violations),
    )


def _apply_rules(
    dataset: Dataset,
    plan_routes: Mapping[str, Sequence[int | str]],
    ruleset: RuleSet,
) -> dict[str, tuple[int | str, ...]]:
    """Expand every planned route through the rule chain, plan order preserved.

    WHY plan order and why unknown vehicles survive here: `validate_routes`
    must number routes the way the official loop over `plan.rutas` does and
    must still report a route whose vehicle is unknown, so the expanded map
    mirrors `plan_routes` exactly (dataset vehicles get their rule-expanded
    stops; an unknown vehicle keeps its raw stops for the error report, since
    `expand` has no `Vehicle` to be called with).
    """
    expanded: dict[str, tuple[int | str, ...]] = {}
    for vehicle_id, raw_route in plan_routes.items():
        vehicle = next((v for v in dataset.vehicles if v.id == vehicle_id), None)
        if vehicle is None:
            expanded[vehicle_id] = tuple(raw_route)
            continue
        expanded[vehicle_id] = ruleset.expand(vehicle, raw_route, dataset)
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
