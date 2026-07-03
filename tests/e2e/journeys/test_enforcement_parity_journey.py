from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.profiles.enforcement_profiles import preset_for_enforcement_level
from orchestrator.workspace_ci_runner import run_enforcement_bundle

pytestmark = pytest.mark.e2e_journey


def test_enforcement_ten_fails_without_tests_then_passes(tmp_path: Path) -> None:
    ws = tmp_path / "app"
    (ws / "src" / "app").mkdir(parents=True)
    (ws / "src" / "app" / "calculator.py").write_text(
        "def add(a, b):\n    return a + b\n",
        encoding="utf-8",
    )
    (ws / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["src"]\ntestpaths = ["tests"]\n',
        encoding="utf-8",
    )
    profile = preset_for_enforcement_level(10)
    fail_result = run_enforcement_bundle(ws, profile, milestone=True, timeout_seconds=180.0)
    assert fail_result.passed is False

    (ws / "tests").mkdir()
    (ws / "tests" / "test_calculator.py").write_text(
        "from app.calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )
    pass_result = run_enforcement_bundle(ws, profile, milestone=True, timeout_seconds=180.0)
    pytest_steps = [s for s in pass_result.steps if s.name.startswith("pytest")]
    assert pytest_steps
    assert all(s.exit_code == 0 for s in pytest_steps)
