from __future__ import annotations

from pathlib import Path
from typing import Any

from standards.stream_results import CheckResult


def check_n_plus_one(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    from orchestrator.critique.performance_scan import scan_n_plus_one_heuristic

    code, detail = scan_n_plus_one_heuristic(workspace)
    return CheckResult(
        check_id="perf.n_plus_one_heuristic",
        passed=code == 0,
        verdict="warn",
        detail=detail[:4000],
        exit_code=code,
    )


def check_ruff_perf(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    from orchestrator.critique.performance_scan import run_ruff_perf

    code, detail = run_ruff_perf(workspace)
    return CheckResult(
        check_id="perf.ruff_perflint",
        passed=code == 0,
        verdict="warn",
        detail=detail[:4000],
        exit_code=code,
    )
