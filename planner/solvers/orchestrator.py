"""Search over vehicle counts and offsets, scoring via the official simulator."""

from __future__ import annotations

import time
from dataclasses import replace

from planner.domain.models import Dataset, Evaluation, Plan
from planner.rules.base import RuleSet
from planner.simulation import simulate
from planner.solvers.base import SolveContext
from planner.solvers.construction import SweepConstructor
from planner.solvers.improvement import LocalSearch, Relocate, Swap, TwoOpt


class Orchestrator:
    """Compose construction and local improvement, retaining the best plan."""

    def __init__(self) -> None:
        self.constructor = SweepConstructor()
        self.operators = (TwoOpt(), Relocate(), Swap())

    def solve(self, ds: Dataset, rules: RuleSet, ctx: SolveContext) -> Plan:
        """Try feasible vehicle counts and sweep offsets until the deadline.

        Orders rejected by the active rules are left out deliberately: the
        simulator then reports them as unserved failures, keeping plans valid.
        """
        eligible = {
            order_id: order for order_id, order in ds.orders.items() if rules.assignable(order, ds)
        }
        if not eligible or not ds.vehicles:
            return Plan(routes={})

        construction_dataset = replace(ds, orders=eligible)
        best_plan: Plan | None = None
        best_evaluation: Evaluation | None = None
        max_vehicles = min(len(ds.vehicles), len(eligible))

        for k in range(1, max_vehicles + 1):
            best_for_k: Evaluation | None = None
            offset_count = min(len(eligible), max(1, k))
            for offset in range(offset_count):
                if self._expired(ctx.deadline) and best_plan is not None:
                    break
                routes = self.constructor.build(construction_dataset, k, offset)
                plan = self._plan_for_routes(ds, routes)
                local_search = LocalSearch(
                    self.operators,
                    evaluate=lambda candidate: self._evaluate_routes(ds, rules, candidate),
                )
                routes = local_search.improve(routes, ctx.deadline)
                plan = self._plan_for_routes(ds, routes)
                evaluation = simulate(ds, plan, rules)

                if best_for_k is None or evaluation.total < best_for_k.total:
                    best_for_k = evaluation
                if best_evaluation is None or evaluation.total < best_evaluation.total:
                    best_plan = plan
                    best_evaluation = evaluation
                if self._expired(ctx.deadline):
                    break

            if best_for_k is not None:
                ctx.log.info("k=%d costo=%d", k, best_for_k.total)
            if self._expired(ctx.deadline) and best_plan is not None:
                break

        # If deadline expired before any candidate was evaluated, ensure a
        # valid, deterministic baseline is still returned.
        if best_plan is None:
            routes = self.constructor.build(construction_dataset, 1, 0)
            best_plan = self._plan_for_routes(ds, routes)
        return best_plan

    @staticmethod
    def _plan_for_routes(dataset: Dataset, routes: list[list[int]]) -> Plan:
        return Plan(
            routes={
                dataset.vehicles[index].id: tuple(route)
                for index, route in enumerate(routes)
                if route
            }
        )

    @staticmethod
    def _evaluate_routes(dataset: Dataset, rules: RuleSet, routes: list[list[int]]) -> int:
        return simulate(dataset, Orchestrator._plan_for_routes(dataset, routes), rules).total

    @staticmethod
    def _expired(deadline: float | None) -> bool:
        return deadline is not None and time.monotonic() >= deadline


__all__ = ["Orchestrator"]
