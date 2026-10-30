"""Rule protocol and RuleSet: the extension point every event rule plugs into.

Why a Protocol instead of an ABC: docs/04-patrones.md forbids single-use ABCs
and favors composition; a rule is any class with this shape, and the neutral
defaults below mean an incomplete rule is inert (never applies, costs nothing,
assigns everything) rather than broken. Concrete rules inherit from `Rule` to
get the defaults for free (PEP 544 explicit subclassing) — as first exercised
by this very task's tests.

`rules` imports only `planner.domain` (docs/03 dependency arrow), so a rule
cannot reach the simulator or a solver: the cost stays in `simulation/`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import planner.rules.registry as rule_registry
from planner.domain.models import Dataset, Evaluation, Order, Vehicle


class Rule(Protocol):
    """One event rule. Add a new rule = new file + one `register` line.

    `name` identifies the rule in the cost breakdown (key = `rule.name`).
    Default bodies are the neutral choices: a rule that does not override
    `applies` never activates, and the remaining defaults are no-ops so the
    active chain (`RuleSet`) stays cheap and silent.
    """

    name: str

    def applies(self, dataset: Dataset) -> bool:
        """Activate on a dataset only if it carries this rule's fields."""
        return False

    def expand(
        self, vehicle: Vehicle, route: Sequence[int | str], ds: Dataset
    ) -> Sequence[int | str]:
        """Turn the rewritten-so-far route into this rule's stops (e.g. insert
        DEPOSITO). Why `int | str` (docs/03 says `Sequence[int]`): in the chain
        every rule's output feeds the next rule's input, and that output may
        already carry `DEPOSITO` stops."""
        return list(route)

    def check(self, vehicle: Vehicle, stops: Sequence[int | str], ds: Dataset) -> list[str]:
        """Feasibility violations for one vehicle's expanded stops."""
        return []

    def extra_cost(self, evaluation: Evaluation, ds: Dataset) -> int:
        """Additional cost line this rule charges (gets its own breakdown key)."""
        return 0

    def assignable(self, order: Order, ds: Dataset) -> bool:
        """Whether this rule lets `order` be assigned at all (consumed from T9)."""
        return True


@dataclass(frozen=True, slots=True)
class RuleSet:
    """Active rules in chain order (docs/04: Registry + Chain of Responsibility).

    The tuple holds only rules that already answered `applies(dataset) == True`
    (direct construction is pre-filtered; `from_dataset` does the filtering).
    An empty set is the identity: routes intact, no cost, no violations.
    """

    rules: tuple[Rule, ...] = ()

    @classmethod
    def from_dataset(cls, dataset: Dataset) -> RuleSet:
        """Filter `REGISTRY` by `applies(dataset)`, keeping registration order.

        Reads `registry.REGISTRY` through the module at call time (not an
        import-time copy) so tests can monkeypatch the registry in isolation.
        """
        from planner.rules.premium import PremiumRule

        if PremiumRule not in rule_registry.REGISTRY:
            rule_registry.register(PremiumRule)
        active: list[Rule] = []
        for rule_type in rule_registry.REGISTRY:
            rule = rule_type()
            if rule.applies(dataset):
                active.append(rule)
        return cls(tuple(active))

    def expand(
        self, vehicle: Vehicle, route: Sequence[int | str], ds: Dataset
    ) -> tuple[int | str, ...]:
        """Chain of Responsibility: each active rule rewrites the previous
        rule's stops. The vehicle id is lookup-free: pass the `Vehicle`."""
        stops: tuple[int | str, ...] = tuple(route)
        for rule in self.rules:
            stops = tuple(rule.expand(vehicle, stops, ds))
        return stops

    def check(self, vehicle: Vehicle, stops: Sequence[int | str], ds: Dataset) -> list[str]:
        """All active rules' feasibility violations, in registration order."""
        violations: list[str] = []
        for rule in self.rules:
            violations.extend(rule.check(vehicle, stops, ds))
        return violations

    def extra_breakdown(self, evaluation: Evaluation, ds: Dataset) -> dict[str, int]:
        """`rule.name` -> cost amount, accumulated per name.

        Why the simulator needs this (and not only `extra_cost`): the official
        breakdown is keyed by line name, so each rule's term must be labeled.
        Rules receive the base evaluation (official terms only): no rule sees
        another rule's cost, keeping the total order-independent. Zero amounts
        are included for completeness; `simulate` drops them so a costless
        active rule never alters the evaluation.
        """
        amounts: dict[str, int] = {}
        for rule in self.rules:
            amounts[rule.name] = amounts.get(rule.name, 0) + rule.extra_cost(evaluation, ds)
        return amounts

    def extra_cost(self, evaluation: Evaluation, ds: Dataset) -> int:
        """Sum of every active rule's cost term."""
        return sum(self.extra_breakdown(evaluation, ds).values())

    def assignable(self, order: Order, ds: Dataset) -> bool:
        """True only if every active rule allows assigning `order`.

        `all()` short-circuits, so a forbidding rule skips the rest of the
        chain (consumed by solvers from T9, wiring exists from today).
        """
        return all(rule.assignable(order, ds) for rule in self.rules)


def as_ruleset(rules: RuleSet | Sequence[Rule] | None) -> RuleSet:
    """Normalize legacy `simulate` callers into a `RuleSet`.

    Why: `simulate(dataset, plan, rules)` was duck-typed in T3 (`None` or an
    iterable of objects with `expand`); keeping that shape working preserves
    the 76 pre-T4 tests while the final arrow `simulation -> rules -> domain`
    is already in place. New code should pass a `RuleSet` directly.
    """
    if rules is None:
        return RuleSet()
    if isinstance(rules, RuleSet):
        return rules
    return RuleSet(tuple(rules))


#: No module-level state here on purpose: the only registry is `registry.REGISTRY`
#: and rules are stateless value classes instantiated on demand by `from_dataset`.
__all__ = ["Rule", "RuleSet", "as_ruleset"]
