from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.enforcement_profiles import preset_for_enforcement_level
from nimbusware_orchestrator.workspace_ci_runner import (
    parity_contract_steps,
    run_enforcement_bundle,
)


def test_parity_contract_steps() -> None:
    steps = parity_contract_steps()
    assert "ruff_check" in steps
    assert "pytest_coverage" in steps
    assert "pip_audit" in steps


def test_enforcement_bundle_sketch_level(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "main.py").write_text("x=1\n", encoding="utf-8")
    profile = preset_for_enforcement_level(0)
    result = run_enforcement_bundle(ws, profile, scope_paths=["main.py"])
    assert result.passed is True
    assert result.layout is not None


def test_enforcement_mapped_tests_fail_at_level_4(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    (ws / "src").mkdir()
    (ws / "src" / "calc.py").write_text("def add(a,b): return a+b\n", encoding="utf-8")
    profile = preset_for_enforcement_level(4)
    result = run_enforcement_bundle(
        ws,
        profile,
        scope_paths=["src/calc.py"],
    )
    assert result.passed is False
    assert any(s.name == "pytest_mapped" for s in result.steps)


def test_run_workspace_ci_parity_on_tiny_fixture() -> None:
    root = Path(__file__).resolve().parents[1]
    fixture = root / "fixtures" / "repos" / "tiny_python_app"
    if not fixture.is_dir():
        return
    profile = preset_for_enforcement_level(10)
    result = run_enforcement_bundle(
        fixture,
        profile,
        scope_paths=["src/app/calculator.py"],
        milestone=True,
    )
    assert result.layout is not None
    assert "src" in result.layout.source_roots or result.layout.source_roots
