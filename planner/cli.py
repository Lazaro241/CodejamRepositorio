"""Command-line pipeline for reading, solving, validating and writing a plan."""

from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Sequence
from pathlib import Path

from planner.io import DatasetError, read_dataset, write_plan
from planner.rules.base import RuleSet
from planner.simulation import simulate, validate
from planner.solvers.base import SolveContext
from planner.solvers.orchestrator import Orchestrator


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
    """Run the full planner pipeline; invalid plans never reach a writer."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.budget is not None and args.budget < 0:
        parser.error("--budget debe ser un número no negativo")

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        dataset = read_dataset(Path(args.dataset))
        rules = RuleSet.from_dataset(dataset)
        deadline = time.monotonic() + args.budget if args.budget is not None else None
        context = SolveContext(seed=args.seed, deadline=deadline)
        plan = Orchestrator().solve(dataset, rules, context)

        errors = validate(dataset, plan)
        if errors:
            logging.getLogger(__name__).error("Plan inválido: %s", "; ".join(errors))
            return 2

        evaluation = simulate(dataset, plan, rules)
        if evaluation.violations:
            logging.getLogger(__name__).error(
                "Plan inválido tras aplicar reglas: %s", "; ".join(evaluation.violations)
            )
            return 2

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_plan(plan, output_path)
        if args.csv:
            csv_path = output_path.with_suffix(".csv")
            write_plan(plan, csv_path, as_csv=True)
    except (DatasetError, OSError, ValueError) as error:
        logging.getLogger(__name__).error("Error: %s", error)
        return 2

    print(f"Costo total: {evaluation.total}")
    print("Desglose:")
    for term, amount in evaluation.breakdown.items():
        print(f"  {term}: {amount}")
    if evaluation.unserved:
        print(f"Pedidos no asignados: {', '.join(map(str, evaluation.unserved))}")
    print(f"Plan JSON: {output_path}")
    if args.csv:
        print(f"Plan CSV: {csv_path}")
    return 0
