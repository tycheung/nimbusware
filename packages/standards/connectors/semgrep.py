from __future__ import annotations

from pathlib import Path
from typing import Any

from standards.stream_results import CheckResult


def run_semgrep_check(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    from orchestrator.critique.security_semgrep import run_semgrep_scan

    code, detail = run_semgrep_scan(workspace)
    return CheckResult(
        check_id="semgrep.ci",
        passed=code == 0,
        verdict=params.get("default_verdict") or "warn",
        detail=detail[:4000],
        exit_code=code,
    )
