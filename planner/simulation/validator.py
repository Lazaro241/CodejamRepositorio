"""Plan validity (official spec §5), replicating the official `validar_plan`.

An invalid plan scores 0 for the whole dataset, so this check always runs
before a plan is written or scored. Mirrors `quickdrop-sim/quickdrop/
simulador.py::validar_plan` exactly: same four error conditions, same report
language, and the stops of a route whose vehicle is unknown/repeated are not
further checked (the official loop `continue`s past them).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from planner.domain.models import Dataset, Plan

#: The literal stop a plan uses to send a vehicle back to the depot and start
#: a new trip. Lives here (the first consumer) so `simulator.py` — which
#: imports `validate()` anyway — has one shared value, matching the string
#: `io` reads and writes and the official simulator's `DEPOSITO`.
DEPOSITO = "DEPOSITO"


def validate(dataset: Dataset, plan: Plan) -> list[str]:
    """Contract entry point: validate the plan's routes in plan order.

    Returns the official violations in official order; empty means valid."""
    return validate_routes(dataset, plan.routes)


def validate_routes(dataset: Dataset, routes: Mapping[str, Sequence[int | str]]) -> list[str]:
    """Same check as `validate` for already-expanded routes ({vehicle: stops}).

    WHY the expanded variant: rules (T4) may insert `DEPOSITO` stops; the plan
    that is simulated — the one that would be written — is the expanded one,
    so that is what must be validated. The official simulator validates what
    it is about to simulate too.
    """
    errors: list[str] = []
    seen_vehicles: set[str] = set()
    seen_orders: dict[int, str] = {}
    for index, (vehicle_id, stops) in enumerate(routes.items(), start=1):
        # NOTE: with a mapping-keyed Plan a repeated vehicle cannot even be
        # expressed, but the check stays for exact parity with the official
        # contract (e.g. if a route sequence is ever validated before freezing).
        if vehicle_id not in {vehicle.id for vehicle in dataset.vehicles}:
            errors.append(f"Ruta {index}: el vehículo '{vehicle_id}' no existe.")
            continue
        if vehicle_id in seen_vehicles:
            errors.append(f"El vehículo '{vehicle_id}' aparece en más de una ruta.")
            continue
        seen_vehicles.add(vehicle_id)
        for stop in stops:
            if stop == DEPOSITO:
                continue
            if not isinstance(stop, int) or stop not in dataset.orders:
                errors.append(f"Vehículo {vehicle_id}: el pedido {stop} no existe.")
                continue
            if stop in seen_orders:
                first = seen_orders[stop]
                errors.append(
                    f"El pedido {stop} aparece más de una vez (vehículos {first} y {vehicle_id})."
                )
                continue
            seen_orders[stop] = vehicle_id
    return errors


__all__ = ["DEPOSITO", "validate", "validate_routes"]
