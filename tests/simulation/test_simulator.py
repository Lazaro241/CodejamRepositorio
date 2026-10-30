"""Simulator unit tests: official semantics on small synthetic datasets.

Money-shape cases here complement the fixed parity cases in
`test_parity.py` (which pin real official-simulator outputs): invalid plans,
failures, reload trips, the "used vehicle" definition and the rules hook.
"""

from __future__ import annotations

from collections.abc import Sequence

from planner.domain.models import Dataset, Order, Plan, Vehicle, World
from planner.rules.base import Rule
from planner.simulation import simulate

_WORLD = World(
    width=20,
    height=20,
    depot=(0, 0),
    departure=480,
    service_time=5,
    load_time=10,
    minutes_per_block=3,
    cost_per_block=3,
    cost_per_vehicle=60,
    cost_per_minute=1,
    cost_per_failure=200,
)


def _dataset(orders: list[Order], vehicles: tuple[str, ...]) -> Dataset:
    return Dataset(
        world=_WORLD,
        orders={o.id: o for o in orders},
        vehicles=tuple(Vehicle(id) for id in vehicles),
    )


def _orders() -> list[Order]:
    return [
        Order(1, 6, 2, 1),
        Order(2, 3, 4, 1),
        Order(3, 10, 10, 1),
    ]


def test_missing_orders_fail_without_invalidating() -> None:
    # Official: a plan is valid (score is computed) and each absent order pays
    # costo_por_falla; unserved lists them in dataset order.
    dataset = _dataset(_orders(), ("V1",))
    evaluation = simulate(dataset, Plan({"V1": (1,)}), rules=None)
    assert evaluation.violations == ()
    assert evaluation.unserved == (2, 3)
    blocks = 8 + 8  # depot->{6,2} with the symmetric final return
    assert evaluation.breakdown == {
        "distancia": blocks * 3,
        "vehiculos": 60,
        "tiempo": blocks * 3 + 5,  # travel + service of the single delivery
        "fallas": 2 * 200,
    }
    assert evaluation.total == sum(evaluation.breakdown.values())


def test_invalid_plan_scores_zero_like_official() -> None:
    # Official `Resultado(valido=False, errores=...)`: no simulation, no cost.
    dataset = _dataset(_orders(), ("V1",))
    evaluation = simulate(dataset, Plan({"V2": (1, 2, 3)}), rules=None)
    assert evaluation.total == 0
    assert evaluation.breakdown == {}
    assert evaluation.unserved == ()
    assert evaluation.violations == ("Ruta 1: el vehículo 'V2' no existe.",)


def test_invalid_repeated_order_scores_zero() -> None:
    dataset = _dataset(_orders(), ("V1", "V2"))
    plan = Plan({"V1": (1, 2), "V2": (2,)})
    evaluation = simulate(
        dataset,
        plan,
        rules=None,
    )
    assert evaluation.total == 0
    assert evaluation.violations == ("El pedido 2 aparece más de una vez (vehículos V1 y V2).",)


def test_reload_trip_is_official_legal_and_accumulates() -> None:
    dataset = _dataset([Order(1, 4, 0, 1), Order(2, 10, 0, 1), Order(3, 10, 0, 1)], ("V1",))
    evaluation = simulate(dataset, Plan({"V1": (1, 2, "DEPOSITO", 3)}), rules=None)
    assert evaluation.violations == ()
    assert evaluation.unserved == ()
    assert evaluation.breakdown == {
        "distancia": 40 * 3,  # 4 + 6 + 10(recarga) + 10 + 10(regreso) blocks
        "vehiculos": 60,
        "tiempo": 145,  # travel 120 + 3 services of 5 + load 10 = 145
        "fallas": 0,
    }


def test_vehicle_with_only_deposito_stops_is_not_used() -> None:
    dataset = _dataset([Order(1, 6, 2, 1)], ("V1", "V2"))
    evaluation = simulate(dataset, Plan({"V1": (), "V2": ("DEPOSITO", 1)}), rules=None)
    assert evaluation.breakdown["vehiculos"] == 60  # only V2 carries a delivery
    assert evaluation.breakdown["distancia"] == (8 + 8) * 3


def test_empty_plan_makespan_is_zero_and_all_fail() -> None:
    dataset = _dataset(_orders(), ("V1", "V2"))
    evaluation = simulate(dataset, Plan({}), rules=None)
    assert evaluation.violations == ()
    assert evaluation.unserved == (1, 2, 3)
    assert evaluation.breakdown == {
        "distancia": 0,
        "vehiculos": 0,
        "tiempo": 0,
        "fallas": 600,
    }


class _RuleEveryTwoStops(Rule):
    """Fake rule: insert DEPOSITO after every 2 order stops.

    Since T4 wires the full rule interface in `simulate`, it inherits the
    neutral defaults (`applies`/`check`/`extra_cost`/`assignable`) from the
    protocol instead of remaining the T3 duck-typed slice.
    """

    name = "fake"

    def expand(self, vehicle: Vehicle, route: Sequence[int], ds: Dataset) -> Sequence[int | str]:
        stops: list[int | str] = []
        for index, stop in enumerate(route, start=1):
            stops.append(stop)
            if index % 2 == 0 and index < len(route):
                stops.append("DEPOSITO")
        return stops


def test_rules_chain_and_none_means_no_rules() -> None:
    dataset = _dataset([Order(1, 4, 0, 1), Order(2, 10, 0, 1), Order(3, 10, 0, 1)], ("V1",))
    manual = Plan({"V1": (1, 2, "DEPOSITO", 3)})
    with_rule = simulate(dataset, Plan({"V1": (1, 2, 3)}), [_RuleEveryTwoStops()])
    manual_result = simulate(dataset, manual, None)
    assert with_rule == manual_result

    plain = simulate(dataset, Plan({"V1": (1, 2, 3)}), None)
    assert plain == simulate(dataset, Plan({"V1": (1, 2, 3)}), [])
    # Different from the manual reload plan: no rule == raw route, no DEPOSITO.
    assert plain.breakdown["distancia"] != with_rule.breakdown["distancia"]
