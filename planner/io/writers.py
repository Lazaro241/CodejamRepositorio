"""Writers for the QuickDrop plan format (docs/02, "Formato del plan").

Strategy + Factory mirrors `readers.py`: `JsonPlanWriter` / `CsvPlanWriter`
serialize a `Plan` and `write_plan` picks one. Writers are io-only on purpose
(docs/03 flow): validation (`validator.validate`) happens in the CLI *before*
writing, so no check lives here — a writer must faithfully dump whatever plan
it receives.

Vehicles with empty routes are omitted because unused vehicles pay no fixed
cost and the official simulator ignores them; writing them would only add
noise for the simulator to (mis)interpret.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Protocol

from planner.domain.models import Plan

_CSV_HEADER: tuple[str, str] = ("vehiculo", "parada")


class PlanWriter(Protocol):
    """Strategy protocol: a writer serializes a `Plan` to one file format."""

    def write(self, plan: Plan, path: Path) -> None: ...


def _routes_with_deliveries(plan: Plan) -> list[tuple[str, tuple[int | str, ...]]]:
    """Non-empty routes only, in plan order (mapping iteration order is the
    dataset vehicle order upstream, which keeps output deterministic)."""
    return [(this_id, stops) for this_id, stops in plan.routes.items() if stops]


class JsonPlanWriter:
    """Writes `{"rutas": [{"vehiculo": "V1", "paradas": [2, 1, "DEPOSITO"]}]}`.

    Order ids stay JSON integers and `"DEPOSITO"` stays a string, exactly as
    docs/02 prescribes — the simulator keys stops on those types."""

    def write(self, plan: Plan, path: Path) -> None:
        payload = {
            "rutas": [
                {"vehiculo": vehicle_id, "paradas": list(stops)}
                for vehicle_id, stops in _routes_with_deliveries(plan)
            ]
        }
        with path.open("w", encoding="utf-8") as handle:
            # Compact separators: byte-stable, matches the doc sample shape.
            handle.write(json.dumps(payload, separators=(",", ":")))


class CsvPlanWriter:
    """Writes `vehiculo,parada` with one row per stop (docs/02 plan CSV)."""

    def write(self, plan: Plan, path: Path) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(_CSV_HEADER)
            for vehicle_id, stops in _routes_with_deliveries(plan):
                for stop in stops:
                    writer.writerow([vehicle_id, stop])


def plan_writer(as_csv: bool = False) -> PlanWriter:
    """Factory: the strategy for the requested format."""
    return CsvPlanWriter() if as_csv else JsonPlanWriter()


def write_plan(plan: Plan, path: str | Path, as_csv: bool = False) -> Path:
    """Write `plan` to `path` as JSON (or CSV with `as_csv=True`).

    The flag is named `as_csv` instead of `csv` on purpose: it would shadow the
    stdlib `csv` module this module imports."""
    target = Path(path)
    plan_writer(as_csv).write(plan, target)
    return target
