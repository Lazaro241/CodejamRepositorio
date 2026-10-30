"""End-to-end tests for the CLI pipeline and output formats."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from planner.cli import main
from planner.domain.models import Plan
from planner.io import read_dataset
from planner.simulation import simulate

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _read_json_plan(path: Path) -> Plan:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Plan({route["vehiculo"]: tuple(route["paradas"]) for route in payload["rutas"]})


def _make_dataset(folder: Path, depot: tuple[int, int]) -> Path:
    folder.mkdir()
    world = {
        "grilla_ancho": 30,
        "grilla_alto": 30,
        "deposito_x": depot[0],
        "deposito_y": depot[1],
        "hora_salida": "08:00",
        "tiempo_servicio": 5,
        "tiempo_carga": 10,
        "min_por_cuadra": 3,
        "costo_por_cuadra": 3,
        "costo_por_vehiculo": 60,
        "costo_por_minuto_total": 1,
        "costo_por_falla": 200,
    }
    orders = [
        {"id": 7, "x": depot[0] + 1, "y": depot[1], "peso": 1},
        {"id": 42, "x": depot[0], "y": depot[1] + 1, "peso": 1},
        {"id": 105, "x": depot[0] - 1, "y": depot[1], "peso": 1},
    ]
    vehicles = [{"id": "bike-A"}, {"id": "bike-B"}]
    for name, payload in (("mundo", world), ("pedidos", orders), ("vehiculos", vehicles)):
        (folder / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")
    return folder


def test_cli_runs_practice_dataset_and_csv_matches_simulation(tmp_path: Path, capsys) -> None:
    output = tmp_path / "nested" / "plan.json"
    exit_code = main(
        [
            str(FIXTURES / "practica_n23"),
            "--output",
            str(output),
            "--csv",
            "--seed",
            "17",
            "--budget",
            "0.1",
        ]
    )

    assert exit_code == 0
    csv_path = output.with_suffix(".csv")
    assert output.exists() and csv_path.exists()
    dataset = read_dataset(FIXTURES / "practica_n23")
    evaluation = simulate(dataset, _read_json_plan(output), None)
    output_text = capsys.readouterr().out
    assert f"Costo total: {evaluation.total}" in output_text
    assert all(f"{name}: {amount}" in output_text for name, amount in evaluation.breakdown.items())

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert {row["vehiculo"] for row in rows} <= {vehicle.id for vehicle in dataset.vehicles}


def test_cli_supports_nonzero_depot_and_nonconsecutive_order_ids(tmp_path: Path, capsys) -> None:
    dataset_path = _make_dataset(tmp_path / "dataset", depot=(10, 10))
    output = tmp_path / "plan.json"

    assert main([str(dataset_path), "-o", str(output), "--budget", "0.1"]) == 0

    dataset = read_dataset(dataset_path)
    plan = _read_json_plan(output)
    assert sorted(stop for route in plan.routes.values() for stop in route) == [7, 42, 105]
    assert simulate(dataset, plan, None).total >= 0
    assert "Costo total:" in capsys.readouterr().out


def test_cli_rejects_an_invalid_solver_plan_without_writing(monkeypatch, tmp_path: Path) -> None:
    from planner import cli

    class InvalidSolver:
        def solve(self, ds, rules, ctx) -> Plan:
            return Plan({"missing-vehicle": (next(iter(ds.orders)),)})

    dataset_path = _make_dataset(tmp_path / "dataset", depot=(10, 10))
    output = tmp_path / "invalid.json"
    monkeypatch.setattr(cli, "Orchestrator", InvalidSolver)

    assert main([str(dataset_path), "-o", str(output)]) == 2
    assert not output.exists()
