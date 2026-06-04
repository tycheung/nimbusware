"""per-tool exit codes from ``run_security_scan``."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from hermes_orchestrator.security_scan import run_security_scan


@patch("hermes_orchestrator.security_scan.run_semgrep_scan", return_value=(0, "semgrep ok\n"))
@patch("hermes_orchestrator.security_scan.scan_n_plus_one_heuristic", return_value=(0, "ok\n"))
@patch("hermes_orchestrator.security_scan.run_ruff_perf", return_value=(0, "perf ok\n"))
@patch("hermes_orchestrator.security_scan.run_mypy", return_value=(2, "mypy bad\n"))
@patch("hermes_orchestrator.security_scan.run_bandit", return_value=(0, "bandit ok\n"))
@patch("hermes_orchestrator.security_scan.run_ruff_check", return_value=(1, "ruff bad\n"))
def test_run_security_scan_returns_worst_and_per_tool_exits(
    _mock_ruff: object,
    _mock_bandit: object,
    _mock_mypy: object,
    _mock_perf: object,
    _mock_n1: object,
    _mock_semgrep: object,
    tmp_path: Path,
) -> None:
    worst, log, ruff_ec, bandit_ec, mypy_ec, perf_ec, n1_ec, semgrep_ec = run_security_scan(
        tmp_path,
    )
    assert worst == 2
    assert ruff_ec == 1
    assert bandit_ec == 0
    assert mypy_ec == 2
    assert perf_ec == 0
    assert n1_ec == 0
    assert semgrep_ec == 0
    assert "ruff" in log.lower() and "bandit" in log.lower() and "mypy" in log.lower()
