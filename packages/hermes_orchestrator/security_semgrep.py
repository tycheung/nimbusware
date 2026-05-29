"""Optional semgrep fleet scan for security verify path (PZ-7)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def semgrep_enabled() -> bool:
    raw = os.environ.get("HERMES_RUN_SEMGREP", "1").strip().lower()
    return raw not in ("0", "false", "no")


def run_semgrep_scan(
    workspace: Path,
    *,
    timeout_seconds: float = 180.0,
) -> tuple[int, str]:
    """Run semgrep on ``packages/`` when enabled and on PATH."""
    if not semgrep_enabled():
        return 0, "semgrep skipped (HERMES_RUN_SEMGREP=0)\n"
    exe = shutil.which("semgrep")
    if not exe:
        return 0, "semgrep skipped (not on PATH)\n"
    target = workspace / "packages"
    if not target.is_dir():
        return 0, "semgrep skipped (no packages/)\n"
    config = os.environ.get("HERMES_SEMGREP_CONFIG", "p/ci").strip() or "p/ci"
    proc = subprocess.run(
        [exe, "scan", "--config", config, "--quiet", "--json", str(target)],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
  # semgrep exits 1 when findings exist
    code = 0 if proc.returncode in (0, 1) else proc.returncode
    if proc.returncode == 1:
        code = 1
    return code, f"=== semgrep (exit {proc.returncode}) ===\n{out[:8000]}\n"
