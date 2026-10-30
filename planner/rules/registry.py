"""Registry of rule classes: the one place a new rule gets wired in.

Why a plain ordered list instead of a dict of names: the CHAIN order is the
registration order (docs/04), so appending is all `register` does. Keeping the
registry empty at import time is acceptance for T4: no concrete rule exists
yet, and future rule files just call `@register` at module bottom.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from planner.rules.base import Rule

#: Chain order = registration order. Empty until a rule file registers itself.
REGISTRY: list[type[Rule]] = []


def register(rule_type: type[Rule]) -> type[Rule]:
    """Class decorator: append to `REGISTRY`, keeping insertion order.

    Fails loudly on duplicate names instead of silently shadowing a rule in
    the breakdown, and on a missing class-level `name` (the breakdown keys on
    it, so it must be readable without instantiating).
    """
    name = getattr(rule_type, "name", None)
    if name is None:
        raise ValueError(
            f"{rule_type.__name__} no define 'name' a nivel de clase: el desglose de "
            "costo etiqueta la línea con rule.name."
        )
    if any(getattr(registered, "name", None) == name for registered in REGISTRY):
        raise ValueError(f"la regla '{name}' ya está registrada.")
    REGISTRY.append(rule_type)
    return rule_type


__all__ = ["REGISTRY", "register"]
