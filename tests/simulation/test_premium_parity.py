"""Official parity for the premium event's fixed practice plan."""

from __future__ import annotations

import json
from pathlib import Path

from planner.cli import main
from planner.domain.models import Dataset, Plan
from planner.domain.parsing import parse_bool
from planner.io import CsvReader, JsonReader
from planner.rules.base import RuleSet
from planner.simulation import simulate

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "practica_e1"
_EXPECTED_PREMIUM = {2, 14, 17, 21, 30, 36}
_PLAN = Plan({"V1": tuple(range(1, 41))})


def _premium_ids(dataset: Dataset) -> set[int]:
    return {
        order_id
        for order_id, order in dataset.orders.items()
        if parse_bool(order.extra.get("premium"))
    }


def test_practica_evento1_json_csv_premium_ids_match() -> None:
    json_dataset = JsonReader().read(FIXTURE)
    csv_dataset = CsvReader().read(FIXTURE)

    assert _premium_ids(json_dataset) == _premium_ids(csv_dataset) == _EXPECTED_PREMIUM
    assert (
        int(json_dataset.world.extra["costo_por_minuto_premium"])
        == int(csv_dataset.world.extra["costo_por_minuto_premium"])
        == 1
    )


def test_practica_evento1_matches_official_simulator() -> None:
    dataset = JsonReader().read(FIXTURE)
    evaluation = simulate(dataset, _PLAN, RuleSet.from_dataset(dataset))

    # Official quickdrop-sim a3306ff, fixed route V1=[1..40]: 574 blocks,
    # makespan 1922, premium elapsed starts 5421, total cost 9125.
    assert evaluation.total == 9125
    assert evaluation.breakdown == {
        "distancia": 1722,
        "vehiculos": 60,
        "tiempo": 1922,
        "fallas": 0,
        "premium": 5421,
    }


def test_cli_runs_premium_dataset(tmp_path: Path, capsys) -> None:
    output = tmp_path / "premium-plan.json"

    assert main([str(FIXTURE), "-o", str(output), "--budget", "0.1"]) == 0

    routes = {
        route["vehiculo"]: tuple(route["paradas"])
        for route in json.loads(output.read_text(encoding="utf-8"))["rutas"]
    }
    dataset = JsonReader().read(FIXTURE)
    evaluation = simulate(dataset, Plan(routes), RuleSet.from_dataset(dataset))
    assert evaluation.breakdown["premium"] > 0
    assert f"premium: {evaluation.breakdown['premium']}" in capsys.readouterr().out
