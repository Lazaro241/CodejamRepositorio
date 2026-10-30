"""Smoke test: the package skeleton installs and imports (T0 acceptance)."""

from __future__ import annotations

import pytest


def test_package_imports() -> None:
    # The `-e .` install and `python -m planner` both depend on these imports.
    import planner
    import planner.cli  # noqa: F401


def test_cli_stub_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    from planner.cli import main

    # The stub only prints and exits 0, whatever the dataset folder is.
    assert main(["tests/fixtures/practica_n23"]) == 0
    assert capsys.readouterr().out.strip() == "no implementado"
