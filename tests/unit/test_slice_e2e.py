from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.micro_slice import parse_slice_plan
from nimbusware_orchestrator.slice_e2e import run_slice_e2e_verify
from nimbusware_orchestrator.slice_gate import run_slice_gate_chain
from nimbusware_orchestrator.workflow_blocks_simple import parse_micro_slice_workflow_block


def test_slice_gate_skips_e2e_when_disabled() -> None:
    plan = parse_slice_plan({"slice_id": "s1", "target_paths": ["a.py"]})
    gate = run_slice_gate_chain(
        plan,
        verify_ok=True,
        tests_passed=True,
    )
    e2e = next(s for s in gate.steps if s.name == "slice.e2e")
    assert e2e.verdict == "SKIP"


def test_slice_gate_fails_on_e2e_fail() -> None:
    plan = parse_slice_plan({"slice_id": "s1", "target_paths": ["a.py"]})
    gate = run_slice_gate_chain(
        plan,
        verify_ok=True,
        tests_passed=True,
        e2e_passed=False,
        e2e_detail="playwright failed",
    )
    assert not gate.passed
    e2e = next(s for s in gate.steps if s.name == "slice.e2e")
    assert e2e.verdict == "FAIL"


def test_run_slice_e2e_custom_command(tmp_path: Path) -> None:
    result = run_slice_e2e_verify(
        tmp_path,
        command="python -c \"print('ok')\"",
        timeout_seconds=30.0,
    )
    assert result.verdict == "PASS"


def test_run_slice_e2e_ci_index_html_command(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    result = run_slice_e2e_verify(
        tmp_path,
        command=(
            "python -c \"import pathlib; assert pathlib.Path('index.html').is_file(); print('ok')\""
        ),
        timeout_seconds=30.0,
    )
    assert result.verdict == "PASS"


def test_run_slice_e2e_skips_without_workspace_tests_e2e(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_SLICE_E2E_COMMAND", raising=False)
    result = run_slice_e2e_verify(tmp_path, timeout_seconds=30.0)
    assert result.verdict == "SKIP"
    assert "tests/e2e" in result.detail


def test_run_slice_e2e_skips_control_plane_monorepo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_SLICE_E2E_COMMAND", raising=False)
    repo = find_repo_root()
    result = run_slice_e2e_verify(repo, timeout_seconds=30.0)
    assert result.verdict == "SKIP"
    assert "control-plane" in result.detail


def test_micro_slice_workflow_parses_e2e_enabled_by_default() -> None:
    repo = find_repo_root()
    block = parse_micro_slice_workflow_block(repo, "micro_slice")
    assert block.e2e_enabled is True


def test_micro_slice_web_workflow_parses_e2e_enabled() -> None:
    repo = find_repo_root()
    block = parse_micro_slice_workflow_block(repo, "micro_slice_web")
    assert block.e2e_enabled is True
