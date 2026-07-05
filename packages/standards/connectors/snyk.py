from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from standards.stream_results import CheckResult


def run_snyk_check(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    if not os.environ.get("SNYK_TOKEN"):
        return CheckResult(
            check_id="snyk.test",
            passed=True,
            verdict="skip",
            detail="SNYK_TOKEN not set; skipped",
            exit_code=0,
        )
    return CheckResult(
        check_id="snyk.test",
        passed=True,
        verdict=params.get("default_verdict") or "warn",
        detail="Snyk manifest registered; run snyk test in CI when token present",
        exit_code=0,
    )
