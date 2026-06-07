from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CI = _REPO / ".github" / "workflows" / "ci.yml"
_FLake_MONITOR = _REPO / ".github" / "workflows" / "e2e_flake_monitor.yml"
_SLOW = _REPO / ".github" / "workflows" / "slow_tests.yml"


def test_ci_e2e_job_has_flake_rerun_budget() -> None:
    text = _CI.read_text(encoding="utf-8")
    assert "  e2e:" in text
    assert "--reruns 1" in text
    assert "NIMBUSWARE_E2E_FLAKE_RETRIES" in text


def test_e2e_flake_monitor_workflow_has_weekly_cadence() -> None:
    text = _FLake_MONITOR.read_text(encoding="utf-8")
    assert "schedule:" in text
    assert "--reruns 1" in text
    assert "NIMBUSWARE_E2E_FLAKE_RETRIES" in text
    assert "e2e-flake-failure" in text
    assert "upload-artifact" in text


def test_slow_tests_workflow_includes_stack_soak() -> None:
    text = _SLOW.read_text(encoding="utf-8")
    assert "test_full_replay_stack_soak" in text
    assert "NIMBUSWARE_REPO_ROOT" in text


def test_e2e_conftest_reads_flake_retry_env() -> None:
    path = _REPO / "tests" / "e2e" / "conftest.py"
    body = path.read_text(encoding="utf-8")
    assert "NIMBUSWARE_E2E_FLAKE_RETRIES" in body
