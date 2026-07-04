from __future__ import annotations

from pathlib import Path

from standards.runner import run_bundle, run_check_definition, run_stream
from standards.stream_results import CheckResult


def test_warn_verdict_passes_despite_failure() -> None:
    spec = {
        "id": "demo.warn",
        "default_verdict": "warn",
        "runner": "standards._fixtures:always_fail",
    }
    result = run_check_definition(spec, workspace=Path("."))
    assert result.passed is True
    assert result.verdict == "warn"


def test_hard_gate_fails_on_runner_failure() -> None:
    spec = {
        "id": "demo.hard",
        "default_verdict": "hard_gate",
        "runner": "standards._fixtures:always_fail",
    }
    result = run_check_definition(spec, workspace=Path("."))
    assert result.passed is False
    assert result.verdict == "hard_gate"


def test_architecture_stream_loads_checks() -> None:
    result = run_stream("architecture", workspace=Path("."))
    assert result.stream_id == "architecture"
    assert result.checks
    assert all(isinstance(c, CheckResult) for c in result.checks)


def test_missing_bundle_reports_failure() -> None:
    result = run_bundle("nonexistent-bundle-xyz", workspace=Path("."))
    assert result.passed is False
    assert result.checks[0].check_id == "bundle.missing"
