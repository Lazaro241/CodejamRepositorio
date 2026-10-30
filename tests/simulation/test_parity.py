"""Parity with the official simulator: fixed plans, officially observed costs.

EVERY expected number below was produced by actually running
`python -m quickdrop simular` in `../quickdrop-sim` (2026-10-30); they are
not derived values:

- tests/fixtures/ejemplo (official sample dataset copied as-is) + its
  plan_ejemplo.json -> COSTO TOTAL 1013 (594/180/239/0).
- tests/fixtures/practica_n23 (official practice dataset) + plan_ref.json
  (V1..V5, sequential chunks of 8) -> COSTO TOTAL 2674 (1908/300/466/0).
- tests/fixtures/enunciado_25 (synthetic 25-order dataset reproducing the
  statement case) + plan_ref.json -> COSTO TOTAL 2641 (1290/120/1231/0):
  V1 drives 23 orders (372 blocks -> 3*372 + 23*5 = 1231 min), V2 drives 2
  (58 blocks), 430 blocks total, 2 used vehicles.

If one of these fails, `planner/simulation/` no longer mirrors the official
simulator and must be fixed before anything else.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from planner.domain.models import Evaluation, Plan
from planner.io import CsvReader, JsonReader, read_dataset
from planner.simulation import simulate

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _plan_from_json(path: Path) -> Plan:
    routes = {
        route["vehiculo"]: tuple(route["paradas"])
        for route in json.loads(path.read_text(encoding="utf-8-sig"))["rutas"]
    }
    return Plan(routes)


def test_parity_ejemplo_total_1013() -> None:
    dataset = read_dataset(FIXTURES / "ejemplo")
    plan = _plan_from_json(FIXTURES / "ejemplo" / "plan_ejemplo.json")
    evaluation = simulate(dataset, plan, rules=None)
    assert evaluation == Evaluation(
        total=1013,
        breakdown={"distancia": 594, "vehiculos": 180, "tiempo": 239, "fallas": 0},
        unserved=(),
        violations=(),
    )


def test_parity_practica_n23_total_2674() -> None:
    dataset = read_dataset(FIXTURES / "practica_n23")
    plan = _plan_from_json(FIXTURES / "practica_n23" / "plan_ref.json")
    evaluation = simulate(dataset, plan, rules=None)
    assert evaluation == Evaluation(
        total=2674,
        breakdown={"distancia": 1908, "vehiculos": 300, "tiempo": 466, "fallas": 0},
        unserved=(),
        violations=(),
    )


def test_parity_enunciado_25_total_2641() -> None:
    dataset = read_dataset(FIXTURES / "enunciado_25")
    plan = _plan_from_json(FIXTURES / "enunciado_25" / "plan_ref.json")
    evaluation = simulate(dataset, plan, rules=None)
    assert evaluation == Evaluation(
        total=2641,
        breakdown={"distancia": 1290, "vehiculos": 120, "tiempo": 1231, "fallas": 0},
        unserved=(),
        violations=(),
    )


def _plan_from_csv(path: Path) -> Plan:
    routes: dict[str, list[object]] = {}
    for row in csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()):
        stop: int | str = (
            "DEPOSITO" if row["parada"].strip().upper() == "DEPOSITO" else int(row["parada"])
        )
        routes.setdefault(row["vehiculo"], []).append(stop)
    return Plan({vehicle: tuple(stops) for vehicle, stops in routes.items()})


def test_parity_json_and_csv_encodings_agree() -> None:
    # The official `convertir` command wrote both formats; the parity numbers
    # must not depend on the encoding the dataset was read from.
    enunciado_plan = _plan_from_json(FIXTURES / "enunciado_25" / "plan_ref.json")
    json_dataset = JsonReader().read(FIXTURES / "enunciado_25")
    csv_dataset = CsvReader().read(FIXTURES / "enunciado_25")
    assert simulate(json_dataset, enunciado_plan, rules=None).total == 2641
    assert simulate(csv_dataset, enunciado_plan, rules=None).total == 2641

    ejemplo_json_plan = _plan_from_json(FIXTURES / "ejemplo" / "plan_ejemplo.json")
    ejemplo_csv_plan = _plan_from_csv(FIXTURES / "ejemplo" / "plan_ejemplo.csv")
    ejemplo_dataset = read_dataset(FIXTURES / "ejemplo")
    assert simulate(ejemplo_dataset, ejemplo_json_plan, rules=None).total == 1013
    assert simulate(ejemplo_dataset, ejemplo_csv_plan, rules=None).total == 1013
