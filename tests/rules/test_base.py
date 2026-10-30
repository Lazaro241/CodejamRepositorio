"""Rule protocol tests: inactive extensions are identity operations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest

import planner.rules.registry as rule_registry
from planner.domain.models import Dataset, Evaluation, Order, Plan, Vehicle
from planner.io import read_dataset
from planner.rules.base import Rule, RuleSet
from planner.rules.registry import register
from planner.simulation import simulate

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "practica_n23"


class _NeutralRule(Rule):
    """Rule with no overrides, exercising every neutral protocol default."""

    name = "test_neutral"


class _EveryTwoOrders(Rule):
    """Test rule proving extension activation and route rewriting."""

    name = "test_every_two"

    def applies(self, dataset: Dataset) -> bool:
        return any("test_rule" in vehicle.extra for vehicle in dataset.vehicles)

    def expand(
        self, vehicle: Vehicle, route: Sequence[int | str], ds: Dataset
    ) -> Sequence[int | str]:
        stops: list[int | str] = []
        order_count = 0
        for stop in route:
            stops.append(stop)
            if stop != "DEPOSITO":
                order_count += 1
                if order_count % 2 == 0 and order_count < len(route):
                    stops.append("DEPOSITO")
        return stops


def test_protocol_defaults_are_neutral() -> None:
    rule = _NeutralRule()
    dataset = Dataset(
        world=read_dataset(FIXTURE).world,
        orders={1: Order(1, 0, 0, 1)},
        vehicles=(Vehicle("V1"),),
    )
    evaluation = Evaluation(total=0, breakdown={}, unserved=(), violations=())
    route = (1,)

    assert rule.check(dataset.vehicles[0], route, dataset) == []
    assert rule.extra_cost(evaluation, dataset) == 0
    assert rule.assignable(dataset.orders[1], dataset) is True
    assert rule.applies(dataset) is False
    assert tuple(rule.expand(dataset.vehicles[0], route, dataset)) == route


def test_registry_and_ruleset_activate_only_for_vehicle_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rule_registry, "REGISTRY", [])
    assert register(_EveryTwoOrders) is _EveryTwoOrders
    dataset = read_dataset(FIXTURE)

    assert RuleSet.from_dataset(dataset) == RuleSet()

    vehicle = replace(dataset.vehicles[0], extra={"test_rule": True})
    active_dataset = replace(dataset, vehicles=(vehicle, *dataset.vehicles[1:]))
    ruleset = RuleSet.from_dataset(active_dataset)

    assert len(ruleset.rules) == 1
    assert ruleset.expand(vehicle, (1, 2, 3), active_dataset) == (1, 2, "DEPOSITO", 3)

    order_ids = tuple(dataset.orders)[:3]
    expanded = Plan({vehicle.id: order_ids})
    manual = Plan({vehicle.id: (*order_ids[:2], "DEPOSITO", order_ids[2])})
    assert simulate(active_dataset, expanded, ruleset) == simulate(active_dataset, manual, None)


def test_registry_rejects_duplicate_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rule_registry, "REGISTRY", [])
    register(_EveryTwoOrders)

    class _DuplicateRule(_EveryTwoOrders):
        pass

    with pytest.raises(ValueError, match="ya está registrada"):
        register(_DuplicateRule)


def test_practice_fixture_has_empty_ruleset_and_unchanged_cost() -> None:
    dataset = read_dataset(FIXTURE)
    plan = Plan({dataset.vehicles[0].id: tuple(dataset.orders)})
    ruleset = RuleSet.from_dataset(dataset)

    assert ruleset == RuleSet()
    assert simulate(dataset, plan, ruleset) == simulate(dataset, plan, None)
