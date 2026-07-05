from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from standards.stream_results import CheckResult


def env_skip_check(
    *,
    check_id: str,
    env_names: tuple[str, ...],
    skip_detail: str,
    params: dict[str, Any],
    configured_detail: Callable[[], str],
    require_all: bool = False,
) -> CheckResult:
    if env_names:
        values = [bool(os.environ.get(name)) for name in env_names]
        configured = all(values) if require_all else any(values)
    else:
        configured = False
    if not configured:
        return CheckResult(
            check_id=check_id,
            passed=True,
            verdict="skip",
            detail=skip_detail,
            exit_code=0,
        )
    return CheckResult(
        check_id=check_id,
        passed=True,
        verdict=params.get("default_verdict") or "warn",
        detail=configured_detail(),
        exit_code=0,
    )
