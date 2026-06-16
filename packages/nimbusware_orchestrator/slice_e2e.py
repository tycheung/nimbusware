from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from nimbusware_env.env_flags import env_str


@dataclass(frozen=True)
class SliceE2EResult:
    verdict: str
    detail: str
    exit_code: int | None = None

    @property
    def passed(self) -> bool | None:
        if self.verdict == "PASS":
            return True
        if self.verdict == "FAIL":
            return False
        return None


def _playwright_available() -> bool:
    return shutil.which("playwright") is not None or shutil.which("npx") is not None


def run_slice_e2e_verify(
    workspace: Path,
    *,
    command: str | None = None,
    timeout_seconds: float = 300.0,
) -> SliceE2EResult:
    cmd_line = (command or env_str("NIMBUSWARE_SLICE_E2E_COMMAND")).strip()
    if cmd_line:
        parts = cmd_line.split()
        proc = subprocess.run(
            parts,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        out = ((proc.stdout or "") + (proc.stderr or ""))[:2000]
        if proc.returncode == 0:
            return SliceE2EResult("PASS", out or "e2e command succeeded", proc.returncode)
        return SliceE2EResult("FAIL", out or f"exit {proc.returncode}", proc.returncode)

    if not _playwright_available():
        return SliceE2EResult(
            "SKIP",
            "playwright CLI not on PATH; set slice.e2e.command or NIMBUSWARE_SLICE_E2E_COMMAND",
        )

    probe = subprocess.run(
        ["python", "-m", "playwright", "--version"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=30.0,
    )
    if probe.returncode != 0:
        return SliceE2EResult(
            "SKIP",
            (probe.stderr or probe.stdout or "playwright module not installed")[:500],
            probe.returncode,
        )

    smoke = subprocess.run(
        ["python", "-m", "pytest", "tests/e2e", "-q", "--maxfail=1"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = ((smoke.stdout or "") + (smoke.stderr or ""))[:2000]
    if smoke.returncode == 0:
        return SliceE2EResult("PASS", out or "e2e smoke passed", smoke.returncode)
    if smoke.returncode == 5:
        return SliceE2EResult("SKIP", "no tests/e2e directory in workspace")
    return SliceE2EResult("FAIL", out or f"exit {smoke.returncode}", smoke.returncode)
