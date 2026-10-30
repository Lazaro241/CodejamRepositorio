"""Small pure parsers for optional domain values introduced by event specs."""

from __future__ import annotations

from typing import Any


class DatasetError(ValueError):
    """An input value cannot be interpreted according to the dataset contract."""


def parse_bool(value: Any) -> bool:
    """Parse documented boolean values; missing and blank values mean false."""
    if value is None or value == "":
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"", "0", "false", "no"}:
            return False
        if normalized in {"1", "true", "si", "sí", "yes"}:
            return True
    raise DatasetError(f"booleano inválido: {value!r}")


__all__ = ["DatasetError", "parse_bool"]
