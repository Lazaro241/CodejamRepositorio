"""Per-delivery timestamps needed by event rules that price urgency."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Delivery:
    """One delivered order, timed as minutes after the day's departure."""

    vehicle_id: str
    order_id: int
    start: int
    end: int


__all__ = ["Delivery"]
