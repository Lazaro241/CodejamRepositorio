"""Focused tests for the premium surcharge and its delivery-time semantics."""

from __future__ import annotations

from dataclasses import replace

from planner.domain.models import Dataset, Order, Plan, Vehicle, World
from planner.rules.base import RuleSet
from planner.rules.premium import PremiumRule
from planner.simulation import simulate


def _dataset(*, premium_price: int = 1, premium_first: bool = True) -> Dataset:
    world = World(
        width=10,
        height=10,
        depot=(0, 0),
        departure=480,
        service_time=5,
        load_time=10,
        minutes_per_block=3,
        cost_per_block=3,
        cost_per_vehicle=60,
        cost_per_minute=1,
        cost_per_failure=200,
        extra={"costo_por_minuto_premium": premium_price},
    )
    orders = {
        1: Order(1, 2, 0, 0, {"premium": premium_first}),
        2: Order(2, 4, 0, 0, {"premium": not premium_first}),
    }
    return Dataset(world, orders, (Vehicle("V1"),))


def test_hand_calculated_premium_examples() -> None:
    dataset = _dataset()
    rules = RuleSet((PremiumRule(),))

    premium_first = simulate(dataset, Plan({"V1": (1, 2)}), rules)
    premium_last = simulate(dataset, Plan({"V1": (2, 1)}), rules)

    assert premium_first.total == 124
    assert premium_first.breakdown["premium"] == 6
    assert premium_last.total == 141
    assert premium_last.breakdown["premium"] == 23


def test_premium_in_second_trip_includes_depot_load_time() -> None:
    dataset = _dataset()
    rules = RuleSet((PremiumRule(),))

    evaluation = simulate(dataset, Plan({"V1": (2, "DEPOSITO", 1)}), rules)

    assert evaluation.timeline[-1].start == 45
    assert evaluation.breakdown["premium"] == 45
    assert evaluation.total == 197


def test_unserved_premium_has_no_premium_surcharge() -> None:
    dataset = _dataset()
    evaluation = simulate(dataset, Plan({}), RuleSet((PremiumRule(),)))

    assert evaluation.unserved == (1, 2)
    assert evaluation.breakdown["fallas"] == 400
    assert "premium" not in evaluation.breakdown


def test_zero_price_and_legacy_dataset_keep_expected_costs() -> None:
    event_dataset = _dataset(premium_price=0)
    event_eval = simulate(event_dataset, Plan({"V1": (1, 2)}), RuleSet((PremiumRule(),)))
    assert event_eval.total == 118

    legacy = replace(
        event_dataset,
        world=replace(event_dataset.world, extra={}),
        orders={
            order_id: replace(order, extra={}) for order_id, order in event_dataset.orders.items()
        },
    )
    legacy_eval = simulate(legacy, Plan({"V1": (1, 2)}), RuleSet.from_dataset(legacy))
    assert legacy_eval.total == 118
    assert "premium" not in legacy_eval.breakdown


def test_rule_set_discovers_premium_only_when_present() -> None:
    event_dataset = _dataset()
    assert isinstance(RuleSet.from_dataset(event_dataset).rules[0], PremiumRule)

    legacy = replace(
        event_dataset,
        orders={
            order_id: replace(order, extra={}) for order_id, order in event_dataset.orders.items()
        },
    )
    assert RuleSet.from_dataset(legacy) == RuleSet()
