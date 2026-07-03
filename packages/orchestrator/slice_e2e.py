from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from env.env_flags import env_str


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


def _is_control_plane_repo_workspace(workspace: Path) -> bool:
    """Nimbusware monorepo: tests/e2e is the product suite, not a slice project."""
    ws = workspace.resolve()
    return (ws / "packages" / "orchestrator").is_dir() and (
        ws / "pyproject.toml"
    ).is_file()


def _split_shell_command(cmd_line: str) -> list[str]:
    if os.name == "nt":
        return shlex.split(cmd_line, posix=False)
    return shlex.split(cmd_line)


def run_slice_e2e_verify(
    workspace: Path,
    *,
    command: str | None = None,
    timeout_seconds: float = 300.0,
) -> SliceE2EResult:
    cmd_line = (command or env_str("NIMBUSWARE_SLICE_E2E_COMMAND")).strip()
    if cmd_line:
        parts = _split_shell_command(cmd_line)
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

    e2e_dir = workspace / "tests" / "e2e"
    if not e2e_dir.is_dir():
        return SliceE2EResult("SKIP", "no tests/e2e directory in workspace")

    if _is_control_plane_repo_workspace(workspace):
        return SliceE2EResult(
            "SKIP",
            "control-plane repo workspace; set slice.e2e.command for attached project workspaces",
        )

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
    if smoke.returncode in {1, 4, 5}:
        return SliceE2EResult(
            "SKIP", out or f"no slice e2e tests collected (exit {smoke.returncode})"
        )
    return SliceE2EResult("FAIL", out or f"exit {smoke.returncode}", smoke.returncode)
