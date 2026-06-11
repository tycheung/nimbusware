from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from nimbusware_env.env_flags import env_str, nimbusware_run_semgrep_enabled


def semgrep_enabled() -> bool:
    return nimbusware_run_semgrep_enabled()


def run_semgrep_scan(
    workspace: Path,
    *,
    timeout_seconds: float = 180.0,
) -> tuple[int, str]:
    """Run semgrep on ``packages/`` when enabled and on PATH."""
    if not semgrep_enabled():
        return 0, "semgrep skipped (NIMBUSWARE_RUN_SEMGREP=0)\n"
    exe = shutil.which("semgrep")
    if not exe:
        return 0, "semgrep skipped (not on PATH)\n"
    target = workspace / "packages"
    if not target.is_dir():
        return 0, "semgrep skipped (no packages/)\n"
    config = env_str("NIMBUSWARE_SEMGREP_CONFIG", "p/ci") or "p/ci"
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
