"""Tests for the event's optional premium boolean encodings."""

from __future__ import annotations

import pytest

from planner.domain.parsing import DatasetError, parse_bool


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("1", True),
        ("0", False),
        ("TRUE", True),
        ("False", False),
        ("si", True),
        ("sí", True),
        ("YES", True),
        ("no", False),
        (None, False),
        ("", False),
        ("  ", False),
    ],
)
def test_parse_bool_supported_values(value: object, expected: bool) -> None:
    assert parse_bool(value) is expected


@pytest.mark.parametrize("value", [2, -1, 0.5, "maybe"])
def test_parse_bool_rejects_unknown_values(value: object) -> None:
    with pytest.raises(DatasetError, match="booleano inválido"):
        parse_bool(value)
