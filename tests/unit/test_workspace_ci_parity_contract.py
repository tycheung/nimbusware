from __future__ import annotations

from pathlib import Path

from orchestrator.profiles.enforcement_profiles import preset_for_enforcement_level
from orchestrator.workspace_ci_runner import (
    PARITY_LEVEL,
    parity_contract_steps,
    run_enforcement_bundle,
    run_workspace_ci_parity,
)


def test_parity_level_is_ten() -> None:
    assert PARITY_LEVEL == 10


def test_level_ten_profile_matches_parity_contract() -> None:
    profile = preset_for_enforcement_level(10)
    assert profile.terminal_parity_ci is True
    assert profile.milestone_full_ci is True
    assert profile.ruff_format_check is True
    assert profile.tests_mode == "full_with_coverage"
    assert profile.pip_audit == "required"
    steps = parity_contract_steps()
    assert "ruff_check" in steps
    assert "pytest_coverage" in steps
    assert "bandit" in steps
    assert "mypy" in steps


def test_level_ten_fails_without_tests(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    (ws / "src" / "app").mkdir(parents=True)
    (ws / "src" / "app" / "calc.py").write_text("def add(a,b): return a+b\n", encoding="utf-8")
    (ws / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
        encoding="utf-8",
    )
    profile = preset_for_enforcement_level(10)
    result = run_enforcement_bundle(ws, profile, milestone=True, timeout_seconds=120.0)
    assert result.passed is False
    step_names = {s.name for s in result.steps}
    assert "pytest_coverage" in step_names or "pytest" in step_names


def test_level_ten_passes_with_tests(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    (ws / "src" / "app").mkdir(parents=True)
    (ws / "src" / "app" / "calc.py").write_text("def add(a,b): return a+b\n", encoding="utf-8")
    (ws / "tests").mkdir()
    (ws / "tests" / "test_calc.py").write_text(
        "from app.calc import add\n\ndef test_add():\n    assert add(1,2)==3\n",
        encoding="utf-8",
    )
    (ws / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\npythonpath = ["src"]\ntestpaths = ["tests"]\n',
        encoding="utf-8",
    )
    result = run_workspace_ci_parity(ws, timeout_seconds=180.0)
    assert result.layout is not None
    pytest_steps = [s for s in result.steps if s.name.startswith("pytest")]
    assert pytest_steps
    assert all(s.exit_code == 0 for s in pytest_steps)


def test_tiny_python_fixture_parity_when_present() -> None:
    root = Path(__file__).resolve().parents[1]
    fixture = root / "fixtures" / "repos" / "tiny_python_app"
    if not fixture.is_dir():
        return
    result = run_workspace_ci_parity(fixture, timeout_seconds=300.0)
    assert result.layout is not None
    assert any(s.name.startswith("pytest") for s in result.steps)


def test_parity_contract_steps_subset_of_runner() -> None:
    root = Path(__file__).resolve().parents[1]
    fixture = root / "fixtures" / "repos" / "tiny_python_app"
    if not fixture.is_dir():
        return
    profile = preset_for_enforcement_level(10)
    result = run_enforcement_bundle(fixture, profile, milestone=True, timeout_seconds=300.0)
    emitted = {s.name for s in result.steps}
    contract = set(parity_contract_steps())
    optional = {"mypy"}
    assert contract - optional <= emitted
