"""Reader tests: JSON/CSV equivalence on the real fixture + in-memory variants.

Variant datasets are always written from the fixture loaded in memory into
`tmp_path` (docs/05): derived datasets are tests' business, not fixtures to
commit.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from planner.io import CsvReader, DatasetError, JsonReader, detect_reader, read_dataset

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "practica_n23"
STEMS = ("mundo", "pedidos", "vehiculos")

_EPOCH_WORLD = {
    "grilla_ancho": 20,
    "grilla_alto": 20,
    "deposito_x": 0,
    "deposito_y": 0,
    "hora_salida": "08:00",
    "tiempo_servicio": 5,
    "tiempo_carga": 10,
    "min_por_cuadra": 3,
    "costo_por_cuadra": 3,
    "costo_por_vehiculo": 60,
    "costo_por_minuto_total": 1,
    "costo_por_falla": 200,
}


def _fixture_records() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """The real fixture as JSON in memory; the base for every variant."""
    loaded: dict[str, Any] = {}
    for stem in STEMS:
        with (FIXTURE / f"{stem}.json").open("r", encoding="utf-8-sig") as handle:
            loaded[stem] = json.load(handle)
    orders = loaded["pedidos"]
    if isinstance(orders, dict):
        orders = orders["pedidos"]
    return loaded["mundo"], orders, loaded["vehiculos"]


def _dump_csv(folder: Path, stem: str, *, headers: list[str], rows: Sequence[Any]) -> None:
    """Write rows as dicts (DictWriter) or plain cells; `None` exports as empty."""
    with (folder / f"{stem}.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(
            [
                [row[header] for header in headers] if isinstance(row, Mapping) else row
                for row in rows
            ]
        )


def _world_rows(mundo: Mapping[str, Any]) -> list[dict[str, str]]:
    return [{"clave": key, "valor": str(value)} for key, value in mundo.items()]


def dump_variant(
    folder: Path,
    *,
    fmt: str = "json",
    mundo: Mapping[str, Any] | None = None,
    orders: Sequence[Mapping[str, Any]] | None = None,
    vehicles: Sequence[Mapping[str, Any]] | None = None,
) -> Path:
    """Write a (possibly patched) variant of the fixture in JSON or CSV format.

    CSV cells go through `str()` exactly like a real export would, so the CSV
    reader exercises its text-casting path on the same logical values."""
    folder.mkdir(parents=True, exist_ok=True)
    base_mundo, base_orders, base_vehicles = _fixture_records()
    mundo = dict(base_mundo if mundo is None else mundo)
    orders = list(base_orders if orders is None else orders)
    vehicles = list(base_vehicles if vehicles is None else vehicles)
    if fmt == "json":
        payloads = {"mundo": mundo, "pedidos": orders, "vehiculos": vehicles}
        for stem, payload in payloads.items():
            (folder / f"{stem}.json").write_text(json.dumps(payload), encoding="utf-8")
    elif fmt == "csv":
        _dump_csv(folder, "mundo", headers=["clave", "valor"], rows=_world_rows(mundo))
        order_headers = sorted({key for order in orders for key in order})
        _dump_csv(
            folder,
            "pedidos",
            headers=order_headers,
            rows=[[order[header] for header in order_headers] for order in orders],
        )
        _dump_csv(
            folder,
            "vehiculos",
            headers=sorted({key for vehicle in vehicles for key in vehicle}),
            rows=vehicles,
        )
    else:  # pragma: no cover - guarded by tests' own usage
        raise ValueError(f"formato desconocido: {fmt}")
    return folder


def test_real_fixture_json_is_the_preferred_strategy() -> None:
    reader = detect_reader(FIXTURE)
    assert isinstance(reader, JsonReader)


class TestEquivalenceOnRealFixture:
    """docs/05: both formats must give the same Dataset on the real dataset."""

    def test_json_and_csv_produce_the_same_dataset(self) -> None:
        from_json = JsonReader().read(FIXTURE)
        from_csv = CsvReader().read(FIXTURE)
        assert from_json == from_csv
        assert from_csv == read_dataset(FIXTURE)

    def test_expected_shape_of_the_real_dataset(self) -> None:
        dataset = read_dataset(FIXTURE)
        assert len(dataset.orders) == 40
        assert [vehicle.id for vehicle in dataset.vehicles] == ["V1", "V2", "V3", "V4", "V5"]
        assert dataset.world.depot == (0, 0)
        assert dataset.world.departure == 480  # 08:00 -> minutes since midnight
        assert sum(order.weight for order in dataset.orders.values()) == 455

    def test_no_hardcoded_grid_or_costs(self) -> None:
        dataset = read_dataset(FIXTURE)
        world = dataset.world
        assert (world.width, world.height) == (20, 20)  # from the file, not by chance
        assert world.cost_per_vehicle == 60 and world.cost_per_failure == 200
        assert world.service_time == 5 and world.load_time == 10


class TestVariants:
    def test_depot_not_at_origin(self, tmp_path: Path) -> None:
        folder = dump_variant(tmp_path, mundo={**_EPOCH_WORLD, "deposito_x": 10, "deposito_y": 10})
        world = read_dataset(folder).world
        assert world.depot == (10, 10)
        # Other mundo values come from the file too (costs changed on purpose).
        folder_csv = dump_variant(
            tmp_path / "csv",
            fmt="csv",
            mundo={**_EPOCH_WORLD, "deposito_x": 10, "deposito_y": 10, "costo_por_vehiculo": 99},
        )
        world_csv = read_dataset(folder_csv).world
        assert (world_csv.depot, world_csv.cost_per_vehicle) == ((10, 10), 99)

    def test_non_consecutive_order_ids(self, tmp_path: Path) -> None:
        _, orders, vehicles = _fixture_records()
        sparse = [
            dict(order, id=new_id) for new_id, order in zip((5, 9, 200), orders[:3], strict=True)
        ]
        folder = dump_variant(tmp_path, orders=sparse, vehicles=vehicles[:1])
        dataset = read_dataset(folder)
        assert set(dataset.orders) == {5, 9, 200}
        assert dataset.orders[200].weight == orders[2]["peso"]

    def test_unknown_vehicle_field_lands_in_extra(self, tmp_path: Path) -> None:
        _, _, vehicles = _fixture_records()
        extra_json = dump_variant(
            tmp_path / "j", vehicles=[dict(v, capacidad=60) for v in vehicles]
        )
        dataset = read_dataset(extra_json)
        assert all(vehicle.extra == {"capacidad": 60} for vehicle in dataset.vehicles)
        extra_csv = dump_variant(
            tmp_path / "c", fmt="csv", vehicles=[dict(v, capacidad="60") for v in vehicles]
        )
        dataset_csv = read_dataset(extra_csv)
        # WHY the raw text: io must not interpret unknown columns (docs/04).
        assert all(vehicle.extra == {"capacidad": "60"} for vehicle in dataset_csv.vehicles)

    def test_unknown_order_and_world_fields_lands_in_extra(self, tmp_path: Path) -> None:
        _, orders, _ = _fixture_records()
        marked_orders = [dict(o, ventana=30) for o in orders[:2]]
        folder = dump_variant(
            tmp_path, mundo={**_EPOCH_WORLD, "ventana_total": 60}, orders=marked_orders
        )
        dataset = read_dataset(folder)
        assert dataset.world.extra == {"ventana_total": 60}
        assert dataset.orders[1].extra == {"ventana": 30}
        assert dataset.orders[2].extra == {"ventana": 30}

    def test_optional_weight_missing_null_and_empty_becomes_zero(self, tmp_path: Path) -> None:
        base = {"x": 1, "y": 1}
        folder = dump_variant(
            tmp_path,
            orders=[
                {"id": 1, **base, "peso": None},  # null
                {"id": 2, **base, "peso": ""},  # empty
                {"id": 3, **base},  # key entirely absent
                {"id": 4, **base, "peso": 5},  # control: real weight survives
            ],
        )
        dataset = read_dataset(folder)
        assert {order.id: order.weight for order in dataset.orders.values()} == {
            1: 0,
            2: 0,
            3: 0,
            4: 5,
        }

    def test_csv_weight_empty_cell_is_zero(self, tmp_path: Path) -> None:
        folder = dump_variant(
            tmp_path / "csv",
            fmt="csv",
            orders=[
                {"id": 1, "x": 2, "y": 3, "peso": ""},  # empty cell in a real CSV
                {"id": 2, "x": 3, "y": 4, "peso": 7},
            ],
        )
        weights = {order.id: order.weight for order in read_dataset(folder).orders.values()}
        assert weights == {1: 0, 2: 7}

    def test_mundo_csv_values_arrive_as_text_and_are_cast(self, tmp_path: Path) -> None:
        folder = dump_variant(
            tmp_path / "csv",
            fmt="csv",
            mundo={**_EPOCH_WORLD, "hora_salida": "07:30", "min_por_cuadra": 4},
        )
        world = read_dataset(folder).world
        assert world.departure == 450  # "07:30" -> 450 minutes
        assert world.minutes_per_block == 4  # "4" -> 4

    def test_departure_already_in_minutes_is_tolerated(self, tmp_path: Path) -> None:
        folder = dump_variant(tmp_path, mundo={**_EPOCH_WORLD, "hora_salida": 510})
        assert read_dataset(folder).world.departure == 510

    def test_bom_and_crlf_are_tolerated(self, tmp_path: Path) -> None:
        folder = tmp_path / "bom"
        folder.mkdir()
        json_text = json.dumps(_EPOCH_WORLD).replace(",", ",\r\n")
        (folder / "mundo.json").write_bytes(b"\xef\xbb\xbf" + json_text.encode("utf-8"))
        (folder / "pedidos.json").write_bytes(
            b"\xef\xbb\xbf" + json.dumps([{"id": 1, "x": 0, "y": 0}]).encode("utf-8")
        )
        (folder / "vehiculos.json").write_bytes(
            b"\xef\xbb\xbf" + json.dumps([{"id": "V1"}]).encode("utf-8")
        )
        assert read_dataset(folder).world.departure == 480

        csv_folder = tmp_path / "bom_csv"
        csv_folder.mkdir()
        csv_body = "clave,valor\r\n" + "\r\n".join(f"{k},{v}" for k, v in _EPOCH_WORLD.items())
        order_body = "id,x,y,peso\r\n1,2,3,\r\n"
        vehicle_body = "id\r\nV1\r\n"
        for stem, body in (
            ("mundo", csv_body),
            ("pedidos", order_body),
            ("vehiculos", vehicle_body),
        ):
            (csv_folder / f"{stem}.csv").write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))
        dataset = read_dataset(csv_folder)
        assert dataset.world.depot == (0, 0)
        assert dataset.orders[1].weight == 0  # empty CSV cell after BOM/CRLF

    def test_pedidos_json_dict_wrapping_the_list(self, tmp_path: Path) -> None:
        _, orders, _ = _fixture_records()
        folder = dump_variant(tmp_path)
        (folder / "pedidos.json").write_text(json.dumps({"pedidos": orders}), encoding="utf-8")
        assert len(read_dataset(folder).orders) == len(orders)

    def test_json_preferred_when_both_formats_exist(self, tmp_path: Path) -> None:
        folder = dump_variant(tmp_path, mundo={**_EPOCH_WORLD, "costo_por_falla": 999})
        # Same folder now carries both formats with different mundo values:
        # preference for JSON is only proven if read_dataset picks the .json data.
        dump_variant(tmp_path, fmt="csv", mundo={**_EPOCH_WORLD, "costo_por_falla": 1})
        dataset = read_dataset(folder)
        assert dataset.world.cost_per_failure == 999
        assert isinstance(detect_reader(folder), JsonReader)


class TestValidation:
    def test_order_out_of_grid_named_coordinate(self, tmp_path: Path) -> None:
        _, orders, _ = _fixture_records()
        folder = dump_variant(
            tmp_path,
            orders=[*orders[:1], {"id": 7, "x": 3, "y": 25}],
        )
        with pytest.raises(DatasetError, match=r"pedido 7: y=25 fuera de la grilla 20x20"):
            read_dataset(folder)

    def test_order_out_of_grid_negative_x(self, tmp_path: Path) -> None:
        folder = dump_variant(tmp_path, orders=[{"id": 2, "x": -1, "y": 0}])
        with pytest.raises(DatasetError, match=r"pedido 2: x=-1 fuera de la grilla 20x20"):
            read_dataset(folder)

    def test_depot_out_of_grid_is_checked_before_orders(self, tmp_path: Path) -> None:
        folder = dump_variant(
            tmp_path,
            mundo={**_EPOCH_WORLD, "deposito_x": 25},
            orders=[{"id": 1, "x": 3, "y": 25}],  # also invalid: depot error must win
        )
        with pytest.raises(DatasetError, match=r"depósito \(25, 0\) fuera de la grilla 20x20"):
            read_dataset(folder)

    def test_duplicate_order_id(self, tmp_path: Path) -> None:
        _, orders, _ = _fixture_records()
        duplicated = [*orders[:2], dict(orders[0])]
        folder = dump_variant(tmp_path, orders=duplicated)
        with pytest.raises(DatasetError, match=f"pedido {orders[0]['id']}: id duplicado"):
            read_dataset(folder)

    def test_duplicate_vehicle_id(self, tmp_path: Path) -> None:
        folder = dump_variant(
            tmp_path, orders=[{"id": 1, "x": 0, "y": 0}], vehicles=[{"id": "V1"}, {"id": "V1"}]
        )
        with pytest.raises(DatasetError, match="vehiculos\\[1\\]: id 'V1' vacío o duplicado"):
            read_dataset(folder)

    def test_missing_mundo_field_has_actionable_message(self, tmp_path: Path) -> None:
        broken = {k: v for k, v in _EPOCH_WORLD.items() if k != "tiempo_carga"}
        folder = dump_variant(tmp_path, mundo=broken)
        with pytest.raises(DatasetError, match="mundo: faltan los campos \\['tiempo_carga'\\]"):
            read_dataset(folder)

    def test_missing_files_lists_both_formats(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(DatasetError, match="faltan archivos"):
            read_dataset(empty)

    def test_malformed_json_reports_file(self, tmp_path: Path) -> None:
        folder = dump_variant(tmp_path)
        (folder / "mundo.json").write_text("{no json", encoding="utf-8")
        with pytest.raises(DatasetError, match="no es JSON válido"):
            read_dataset(folder)

    def test_invalid_hora_salida(self, tmp_path: Path) -> None:
        folder = dump_variant(tmp_path, mundo={**_EPOCH_WORLD, "hora_salida": "8am"})
        with pytest.raises(DatasetError, match="hora_salida"):
            read_dataset(folder)
