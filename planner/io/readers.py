"""Readers for the QuickDrop dataset format (docs/02-formato-datos.md).

Strategy + Factory (docs/04-patrones.md): `JsonReader` and `CsvReader` normalize
their files into the same canonical shape — a mapping/list of records whose
values may be native JSON types or CSV text, since the int-casting helpers
accept either. Both strategies feed one shared parse/validate pipeline, which
is *why* the same dataset in JSON and CSV is guaranteed to produce the same
`Dataset`.

Spanish dataset field names (`costo_por_cuadra`, `deposito_x`, ...) live only
here, mapped to domain names: per docs/AGENTS.md they must leak nowhere else.
`DatasetError` carries actionable Spanish messages (docs/05-convenciones.md).
"""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from planner.domain.models import Dataset, Order, Vehicle, World
from planner.domain.parsing import DatasetError

#: Dataset file stems; every stem must be present, in a single format.
_FILE_STEMS: tuple[str, ...] = ("mundo", "pedidos", "vehiculos")

#: mundo fields -> World attributes. `hora_salida` is special (HH:MM -> minutes)
#: and handled separately.
_WORLD_INT_FIELDS: Mapping[str, str] = {
    "grilla_ancho": "width",
    "grilla_alto": "height",
    "deposito_x": "depot_x",
    "deposito_y": "depot_y",
    "tiempo_servicio": "service_time",
    "tiempo_carga": "load_time",
    "min_por_cuadra": "minutes_per_block",
    "costo_por_cuadra": "cost_per_block",
    "costo_por_vehiculo": "cost_per_vehicle",
    "costo_por_minuto_total": "cost_per_minute",
    "costo_por_falla": "cost_per_failure",
}

_WORLD_KNOWN_KEYS: frozenset[str] = frozenset(_WORLD_INT_FIELDS) | {"hora_salida"}
_ORDER_KNOWN_KEYS: frozenset[str] = frozenset({"id", "x", "y", "peso"})


class DatasetReader(Protocol):
    """Strategy protocol: a reader turns a dataset folder into a `Dataset`."""

    def read(self, folder: Path) -> Dataset: ...


def detect_reader(folder: Path) -> DatasetReader:
    """Return the reader for `folder`: JSON if all three .json exist, else CSV.

    WHY all-or-nothing instead of per-file mixing: a partially migrated folder
    (JSON for pedidos, CSV for vehiculos) is almost certainly data corruption,
    and mixing would silently hide it behind the "both formats produce the same
    Dataset" guarantee. Failing loudly keeps that guarantee testable."""
    folder = Path(folder)
    json_paths = {stem: folder / f"{stem}.json" for stem in _FILE_STEMS}
    csv_paths = {stem: folder / f"{stem}.csv" for stem in _FILE_STEMS}
    json_missing = [stem for stem, path in json_paths.items() if not path.is_file()]
    csv_missing = [stem for stem, path in csv_paths.items() if not path.is_file()]
    if not json_missing:
        return JsonReader()
    if not csv_missing:
        return CsvReader()
    raise DatasetError(
        f"en '{folder}' faltan archivos: {json_missing} (formato .json) y {csv_missing} (formato .csv)"
    )


def read_dataset(folder: Path) -> Dataset:
    """Read the dataset in whichever format the folder carries (JSON preferred)."""
    return detect_reader(folder).read(Path(folder))


# --------------------------------------------------------------------------
# Casting helpers: CSV values arrive as text, JSON as native types; both code
# paths go through these so the readers stay byte-for-byte equivalent.
# --------------------------------------------------------------------------


def _as_int(value: Any, context: str) -> int:
    """Cast an int or digit-text value to `int`; required, so None/empty raises."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        raise DatasetError(f"{context}: valor ausente (null o vacío)")
    if isinstance(value, bool):
        raise DatasetError(f"{context}: '{value}' no es un entero")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError as exc:
            raise DatasetError(f"{context}: '{value}' no es un entero") from exc
    raise DatasetError(f"{context}: '{value}' no es un entero")


def _optional_int(value: Any, context: str, default: int = 0) -> int:
    """Missing/`null`/empty -> `default`, never an exception (docs/02 rule 2).

    `peso` is the one optional field today: it constrains nothing yet, so a
    half-filled dataset must still load."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return default
    return _as_int(value, context)


def _hhmm_to_minutes(value: Any, context: str) -> int:
    """`"HH:MM"` -> minutes since midnight (08:00 -> 480). A plain int passes
    through: WHY — a hidden dataset may already ship departure in minutes, and
    both encodings mean the same thing."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    text = str(value).strip() if value is not None else ""
    hours_text, separator, minutes_text = text.partition(":")
    if not separator:
        raise DatasetError(f"{context}: '{text}' no tiene formato HH:MM")
    try:
        hours, minutes = int(hours_text), int(minutes_text)
    except ValueError as exc:
        raise DatasetError(f"{context}: '{text}' no tiene formato HH:MM") from exc
    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
        raise DatasetError(f"{context}: '{text}' fuera del rango 00:00..23:59")
    return hours * 60 + minutes


def _extra_fields(raw: Mapping[str, Any], known_keys: frozenset[str]) -> dict[str, Any]:
    """Unknown keys preserved verbatim (docs/02 rule 3): event rules will read
    them from `World.extra` / `Order.extra` / `Vehicle.extra` without editing io."""
    return {key: value for key, value in raw.items() if key not in known_keys}


# --------------------------------------------------------------------------
# Canonical parse (shared pipeline).
# --------------------------------------------------------------------------


def _parse_world(raw: Mapping[str, Any]) -> World:
    missing = [key for key in (*_WORLD_INT_FIELDS, "hora_salida") if key not in raw]
    if missing:
        raise DatasetError(f"mundo: faltan los campos {missing}")
    values = {attr: _as_int(raw[key], f"mundo: {key}") for key, attr in _WORLD_INT_FIELDS.items()}
    return World(
        width=values["width"],
        height=values["height"],
        depot=(values["depot_x"], values["depot_y"]),
        departure=_hhmm_to_minutes(raw["hora_salida"], "mundo: hora_salida"),
        service_time=values["service_time"],
        load_time=values["load_time"],
        minutes_per_block=values["minutes_per_block"],
        cost_per_block=values["cost_per_block"],
        cost_per_vehicle=values["cost_per_vehicle"],
        cost_per_minute=values["cost_per_minute"],
        cost_per_failure=values["cost_per_failure"],
        extra=_extra_fields(raw, _WORLD_KNOWN_KEYS),
    )


def _parse_orders(records: Sequence[Mapping[str, Any]]) -> dict[int, Order]:
    """Orders keep dataset order; ids may skip numbers (docs/02 pedidos)."""
    orders: dict[int, Order] = {}
    for index, raw in enumerate(records):
        missing = [key for key in ("id", "x", "y") if key not in raw]
        if missing:
            raise DatasetError(f"pedidos[{index}]: faltan los campos {missing}")
        order_id = _as_int(raw["id"], f"pedidos[{index}]: id")
        x = _as_int(raw["x"], f"pedido {order_id}: x")
        y = _as_int(raw["y"], f"pedido {order_id}: y")
        # `peso` es opcional: ausente/null/vacío -> 0, nunca excepción.
        weight = _optional_int(raw.get("peso"), f"pedido {order_id}: peso")
        if order_id in orders:
            raise DatasetError(f"pedido {order_id}: id duplicado en los pedidos")
        orders[order_id] = Order(
            id=order_id, x=x, y=y, weight=weight, extra=_extra_fields(raw, _ORDER_KNOWN_KEYS)
        )
    return orders


def _parse_vehicles(records: Sequence[Mapping[str, Any]]) -> tuple[Vehicle, ...]:
    vehicles: list[Vehicle] = []
    seen: set[str] = set()
    for index, raw in enumerate(records):
        if "id" not in raw:
            raise DatasetError(f"vehiculos[{index}]: falta el campo 'id'")
        vehicle_id = raw["id"]
        if not isinstance(vehicle_id, str):
            # WHY cast instead of raising: CSV ids always arrive as text, so a
            # JSON dataset with `{"id": 1}` is the same data in another shape.
            vehicle_id = str(vehicle_id)
        if vehicle_id.strip() == "" or vehicle_id in seen:
            raise DatasetError(f"vehiculos[{index}]: id '{vehicle_id}' vacío o duplicado")
        seen.add(vehicle_id)
        vehicles.append(Vehicle(id=vehicle_id, extra=_extra_fields(raw, frozenset({"id"}))))
    return tuple(vehicles)


def _validate(world: World, orders: Mapping[int, Order]) -> None:
    """Ordered checks (docs/02 rule 5): duplicates already raise during parse,
    so here the depot is checked first and then one order per iteration, in
    dataset order. Grid limits come from the actual world, never hardcoded."""
    width, height = world.width, world.height
    depot_x, depot_y = world.depot
    if not 0 <= depot_x < width or not 0 <= depot_y < height:
        raise DatasetError(f"depósito ({depot_x}, {depot_y}) fuera de la grilla {width}x{height}")
    for order_id, order in orders.items():
        # One coordinate per message, mirroring docs/05's actionable example.
        if not 0 <= order.x < width:
            raise DatasetError(
                f"pedido {order_id}: x={order.x} fuera de la grilla {width}x{height}"
            )
        if not 0 <= order.y < height:
            raise DatasetError(
                f"pedido {order_id}: y={order.y} fuera de la grilla {width}x{height}"
            )


def _build_dataset(
    raw_world: Mapping[str, Any],
    records_orders: Sequence[Mapping[str, Any]],
    records_vehicles: Sequence[Mapping[str, Any]],
) -> Dataset:
    """Shared pipeline used by both strategies: parse, validate, freeze."""
    world = _parse_world(raw_world)
    orders = _parse_orders(records_orders)
    vehicles = _parse_vehicles(records_vehicles)
    _validate(world, orders)
    return Dataset(world=world, orders=orders, vehicles=vehicles)


# --------------------------------------------------------------------------
# File access. utf-8-sig tolerates a BOM and newline="" tolerates CRLF,
# WHY: hidden datasets may be produced on Windows / Excel (docs/02 rule 4).
# --------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except FileNotFoundError:
        raise DatasetError(f"no se encontró '{path}'") from None
    except json.JSONDecodeError as exc:
        raise DatasetError(f"'{path}' no es JSON válido: {exc}") from exc


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    """CSV -> list of `{header: text_cell}` rows (whitespace and BOM stripped)."""
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except FileNotFoundError:
        raise DatasetError(f"no se encontró '{path}'") from None
    except csv.Error as exc:
        raise DatasetError(f"'{path}' no es CSV válido: {exc}") from exc


def _as_records(raw: Any, path: Path) -> Sequence[Mapping[str, Any]]:
    if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
        raise DatasetError(f"'{path}': se esperaba una lista de objetos")
    return raw


def _pedidos_records(raw: Any, path: Path) -> Sequence[Mapping[str, Any]]:
    """`pedidos.json` may be a list or a dict wrapping it (docs/02 pedidos).

    WHY the fallback search: a dict-wrapped order list is an explicitly
    tolerated shape, so look for `pedidos` first and accept any single
    list-valued key before giving up."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        if isinstance(raw.get("pedidos"), list):
            return raw["pedidos"]
        candidates = [value for value in raw.values() if isinstance(value, list)]
        if len(candidates) == 1 and all(isinstance(o, dict) for o in candidates[0]):
            return candidates[0]
    raise DatasetError(f"'{path}': se esperaba una lista de pedidos o un dict con la lista adentro")


class JsonReader:
    """Reads the dataset as JSON; the whole dataset must be JSON (see `detect_reader`)."""

    def read(self, folder: Path) -> Dataset:
        folder = Path(folder)
        paths = {stem: folder / f"{stem}.json" for stem in _FILE_STEMS}
        raw_world = _load_json(paths["mundo"])
        raw_orders = _load_json(paths["pedidos"])
        raw_vehicles = _load_json(paths["vehiculos"])
        return _build_dataset(
            raw_world=_require_object(raw_world, paths["mundo"]),
            records_orders=_pedidos_records(raw_orders, paths["pedidos"]),
            records_vehicles=_as_records(raw_vehicles, paths["vehiculos"]),
        )


def _require_object(raw: Any, path: Path) -> Mapping[str, Any]:
    if not isinstance(raw, dict):
        raise DatasetError(f"'{path}': se esperaba un objeto")
    return raw


class CsvReader:
    """Reads the dataset as CSV. `mundo` uses `clave,valor` rows and every cell
    arrives as text; the shared casting pipeline turns it into ints."""

    def read(self, folder: Path) -> Dataset:
        folder = Path(folder)
        paths = {stem: folder / f"{stem}.csv" for stem in _FILE_STEMS}
        return _build_dataset(
            raw_world=_world_from_csv(_read_csv_rows(paths["mundo"]), paths["mundo"]),
            records_orders=_orders_from_csv(_read_csv_rows(paths["pedidos"]), paths["pedidos"]),
            records_vehicles=_as_records(_read_csv_rows(paths["vehiculos"]), paths["vehiculos"]),
        )


def _world_from_csv(rows: Sequence[Mapping[str, Any]], path: Path) -> Mapping[str, Any]:
    """`(clave, valor)` rows -> the same `clave: valor` mapping a JSON mundo is."""
    world: dict[str, str] = {}
    for index, row in enumerate(rows):
        if "clave" not in row or "valor" not in row:
            raise DatasetError(f"'{path}' fila {index + 2}: se esperaban columnas clave,valor")
        key, value = str(row["clave"]), row["valor"]
        world[key] = "" if value is None else str(value)
    return world


def _orders_from_csv(rows: Sequence[Mapping[str, Any]], path: Path) -> Sequence[Mapping[str, Any]]:
    if rows and "id" not in rows[0]:
        raise DatasetError(f"'{path}': falta la columna 'id'")
    return rows
