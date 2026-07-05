from __future__ import annotations

from pathlib import Path
from typing import Any

from standards.connectors._env_skip import env_skip_check
from standards.stream_results import CheckResult


def run_codeql_check(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    del workspace
    return env_skip_check(
        check_id="codeql.scan",
        env_names=("CODEQL_TOKEN",),
        skip_detail="CODEQL_TOKEN not set; skipped",
        params=params,
        configured_detail=lambda: "CodeQL manifest registered; run via GitHub Advanced Security workflow",
    )
