"""Rules layer: event rules are data-driven extensions of the day's logic.

Only `planner.domain` is imported here (docs/03). Concrete rules live one per
file (`capacity.py`, ...) and self-register via `planner.rules.registry`; with
nothing registered, `RuleSet.from_dataset` yields the empty, identity set.
"""
