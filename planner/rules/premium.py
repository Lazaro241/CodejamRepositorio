"""Premium rule: add elapsed delivery minutes for premium orders."""

from __future__ import annotations

from typing import ClassVar

from planner.domain.models import Dataset, Evaluation
from planner.domain.parsing import parse_bool
from planner.rules.base import Rule
from planner.rules.registry import register


@register
class PremiumRule(Rule):
    """Apply the premium surcharge only when a dataset has premium orders."""

    name: ClassVar[str] = "premium"

    def applies(self, dataset: Dataset) -> bool:
        return any(parse_bool(order.extra.get("premium")) for order in dataset.orders.values())

    def extra_cost(self, evaluation: Evaluation, ds: Dataset) -> int:
        """Charge premium price times each delivered order's start offset."""
        price = int(ds.world.extra.get("costo_por_minuto_premium", 1))
        start_by_order = {delivery.order_id: delivery.start for delivery in evaluation.timeline}
        return price * sum(
            start_by_order.get(order_id, 0)
            for order_id, order in ds.orders.items()
            if parse_bool(order.extra.get("premium"))
        )


__all__ = ["PremiumRule"]
