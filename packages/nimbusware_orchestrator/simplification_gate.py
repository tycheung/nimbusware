"""Gates simplification slices that delete code behind a passing test suite."""

from __future__ import annotations

import subprocess
from pathlib import Path


def delete_with_tests_allowed(
    workspace: Path,
    target_paths: tuple[str, ...] | list[str],
    *,
    timeout_seconds: float = 60.0,
) -> tuple[bool, str]:
    """Return ``(allowed, detail)`` — deletions require ``tests/`` and green pytest."""
    ws = workspace.resolve()
    if not target_paths:
        return True, "no_targets"
    tests_dir = ws / "tests"
    if not tests_dir.is_dir():
        return False, "missing_tests_dir"
    proc = subprocess.run(
        ["python", "-m", "pytest", "tests", "-q", "--tb=no", "-x"],
        cwd=ws,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if proc.returncode == 0:
        return True, "tests_pass"
    return False, "tests_failed"
