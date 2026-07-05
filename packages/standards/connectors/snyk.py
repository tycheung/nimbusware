from __future__ import annotations

from pathlib import Path
from typing import Any

from standards.connectors._env_skip import env_skip_check
from standards.stream_results import CheckResult


def run_snyk_check(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    del workspace
    return env_skip_check(
        check_id="snyk.test",
        env_names=("SNYK_TOKEN",),
        skip_detail="SNYK_TOKEN not set; skipped",
        params=params,
        configured_detail=lambda: (
            "Snyk manifest registered; run snyk test in CI when token present"
        ),
    )
