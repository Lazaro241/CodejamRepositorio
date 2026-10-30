"""Smoke test: the package skeleton installs and imports (T0 acceptance)."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_package_imports() -> None:
    # The `-e .` install and `python -m planner` both depend on these imports.
    import planner
    import planner.cli  # noqa: F401


def test_cli_runs_pipeline(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    from planner.cli import main

    fixture = Path(__file__).parent / "fixtures" / "practica_n23"
    output = tmp_path / "plan.json"
    assert main([str(fixture), "-o", str(output), "--budget", "0.02"]) == 0
    assert output.exists()
    assert "Costo total:" in capsys.readouterr().out
