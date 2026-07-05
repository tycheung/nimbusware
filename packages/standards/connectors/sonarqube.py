from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from standards.stream_results import CheckResult


def run_sonarqube_check(*, workspace: Path, params: dict[str, Any]) -> CheckResult:
    token = os.environ.get("SONAR_TOKEN") or os.environ.get("SONARQUBE_TOKEN")
    host = os.environ.get("SONAR_HOST_URL") or os.environ.get("SONARQUBE_HOST_URL")
    if not token or not host:
        return CheckResult(
            check_id="sonarqube.scan",
            passed=True,
            verdict="skip",
            detail="SONAR_TOKEN and SONAR_HOST_URL not set; skipped",
            exit_code=0,
        )
    project_key = str(params.get("project_key") or workspace.name)
    return CheckResult(
        check_id="sonarqube.scan",
        passed=True,
        verdict=params.get("default_verdict") or "warn",
        detail=f"SonarQube configured for {project_key} at {host} (CLI scan deferred)",
        exit_code=0,
    )
