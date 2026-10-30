"""CLI stub for the planner (T0).

Accepts the arguments of docs/AGENTS.md; the pipeline (read -> solve -> validate ->
write) is not wired yet, so it only acknowledges the invocation and exits 0 until
T8 implements it. `logging` is unused here because there is no flow to log yet.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with the contract of docs/AGENTS.md."""
    parser = argparse.ArgumentParser(
        prog="python -m planner",
        description="Lee un dataset (mundo, pedidos, vehiculos) y escribe un plan de reparto.",
    )
    parser.add_argument("dataset", help="carpeta del dataset (mundo, pedidos, vehiculos)")
    parser.add_argument(
        "-o", "--output", default="out/plan.json", help="plan de salida (default: out/plan.json)"
    )
    parser.add_argument(
        "--csv", action="store_true", help="escribir el plan tambien en CSV junto al JSON"
    )
    parser.add_argument("--seed", type=int, default=0, help="semilla aleatoria (default: 0)")
    parser.add_argument(
        "--budget",
        type=float,
        default=None,
        help="presupuesto de tiempo de solucion en segundos (opcional)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point: parse arguments; the solve step is a stub for now."""
    # Validation of the argument contract is the only behavior for now.
    build_parser().parse_args(argv)
    print("no implementado")
    return 0
