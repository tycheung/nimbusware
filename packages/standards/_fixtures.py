from __future__ import annotations

from pathlib import Path
from typing import Any

from standards.stream_results import CheckResult


def always_fail(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    _ = workspace, params
    return CheckResult(
        check_id="fixture.fail",
        passed=False,
        verdict="hard_gate",
        detail="intentional failure",
        exit_code=1,
    )
