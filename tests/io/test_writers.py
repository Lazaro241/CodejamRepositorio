"""Writer tests: plan JSON/CSV format per docs/02 ("Formato del plan")."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from planner.domain.models import Plan
from planner.io import CsvPlanWriter, write_plan

_SAMPLE = Plan(
    routes={
        "V1": (2, 1, 10, "DEPOSITO", 8, 3),
        "V2": (),  # no deliveries: must be omitted in both formats
        "V3": (1, "DEPOSITO"),
    }
)


class TestJsonPlanWriter:
    def test_exact_format(self, tmp_path: Path) -> None:
        path = write_plan(_SAMPLE, tmp_path / "plan.json")
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        assert payload == {
            "rutas": [
                {"vehiculo": "V1", "paradas": [2, 1, 10, "DEPOSITO", 8, 3]},
                {"vehiculo": "V3", "paradas": [1, "DEPOSITO"]},
            ]
        }

    def test_order_ids_are_ints_and_deposito_is_a_string(self, tmp_path: Path) -> None:
        path = write_plan(_SAMPLE, tmp_path / "plan.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        paradas = payload["rutas"][0]["paradas"]
        assert paradas[0] == 2 and isinstance(paradas[0], int)
        assert paradas[3] == "DEPOSITO" and isinstance(paradas[3], str)

    def test_empty_routes_are_omitted(self, tmp_path: Path) -> None:
        path = write_plan(_SAMPLE, tmp_path / "plan.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert [route["vehiculo"] for route in payload["rutas"]] == ["V1", "V3"]

    def test_all_routes_empty_yields_empty_plan(self, tmp_path: Path) -> None:
        path = write_plan(Plan(routes={"V1": ()}), tmp_path / "plan.json")
        assert json.loads(path.read_text(encoding="utf-8")) == {"rutas": []}


class TestCsvPlanWriter:
    def test_one_row_per_stop(self, tmp_path: Path) -> None:
        plan = Plan(routes={"V1": (7, 3), "V2": ()})
        path = write_plan(plan, tmp_path / "plan.csv", as_csv=True)
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        assert rows == [
            ["vehiculo", "parada"],
            ["V1", "7"],
            ["V1", "3"],
        ]

    def test_writer_strategy_class_is_used_by_write_plan(self, tmp_path: Path) -> None:
        CsvPlanWriter().write(_SAMPLE, tmp_path / "plan.csv")
        with (tmp_path / "plan.csv").open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        assert rows[0] == ["vehiculo", "parada"]
        assert ["V3", "DEPOSITO"] in rows[1:] and ["V1", "DEPOSITO"] in rows[1:]
        assert not any(vehiculo == "V2" for vehiculo, _ in rows[1:])


class TestRoundTrip:
    def test_json_and_csv_reload_to_the_same_plan(self, tmp_path: Path) -> None:
        """doc 02 keeps ints as ints and "DEPOSITO" as text in both formats, so
        each written file must reload into identical routes."""

        def stop(cell: str) -> int | str:
            return cell if cell == "DEPOSITO" else int(cell)

        json_path = write_plan(_SAMPLE, tmp_path / "plan.json")
        csv_path = write_plan(_SAMPLE, tmp_path / "plan.csv", as_csv=True)

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        json_routes = {r["vehiculo"]: tuple(r["paradas"]) for r in payload["rutas"]}

        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            csv_rows = list(csv.reader(handle))[1:]
        csv_routes: dict[str, tuple[int | str, ...]] = {}
        for vehiculo, parada in csv_rows:
            csv_routes[vehiculo] = (*csv_routes.get(vehiculo, ()), stop(parada))

        # dict-ordered comparison is order-insensitive on keys; route order is
        # stable because both writers iterate plan.routes in the same order.
        assert json_routes == csv_routes
        assert json_routes == {"V1": (2, 1, 10, "DEPOSITO", 8, 3), "V3": (1, "DEPOSITO")}

    def test_write_plan_accepts_str_paths(self, tmp_path: Path) -> None:
        path = write_plan(_SAMPLE, str(tmp_path / "plan.json"))
        assert path.exists()
