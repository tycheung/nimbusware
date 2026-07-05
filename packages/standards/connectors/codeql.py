from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from standards.stream_results import CheckResult


def run_codeql_check(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    if not os.environ.get("CODEQL_TOKEN"):
        return CheckResult(
            check_id="codeql.scan",
            passed=True,
            verdict="skip",
            detail="CODEQL_TOKEN not set; skipped",
            exit_code=0,
        )
    return CheckResult(
        check_id="codeql.scan",
        passed=True,
        verdict=params.get("default_verdict") or "warn",
        detail="CodeQL manifest registered; run via GitHub Advanced Security workflow",
        exit_code=0,
    )
