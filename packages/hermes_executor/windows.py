"""OS-specific subprocess execution for role-gated local commands."""

from __future__ import annotations

import subprocess
from pathlib import Path

from hermes_executor.egress import assert_egress_allowed, host_matches_allowlist


def run_subprocess(
    argv: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: float | None = 300.0,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=env,
        check=False,
    )


__all__ = [
    "assert_egress_allowed",
    "host_matches_allowlist",
    "run_subprocess",
]
