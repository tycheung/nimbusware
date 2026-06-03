from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

VALID_BACKENDS = frozenset({"none", "stub"})


@dataclass(frozen=True)
class SandboxRunResult:
    backend: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def combined_output(self) -> str:
        return (self.stdout or "") + (self.stderr or "")


def resolve_sandbox_backend() -> str:
    raw = os.environ.get("HERMES_SANDBOX_BACKEND", "none").strip().lower()
    if raw not in VALID_BACKENDS:
        return "none"
    return raw


def run_subprocess_in_sandbox(
    workspace: Path,
    argv: list[str],
    *,
    timeout_seconds: float,
    backend: str | None = None,
) -> SandboxRunResult:
    chosen = backend or resolve_sandbox_backend()
    if chosen not in VALID_BACKENDS:
        chosen = "none"
    proc = subprocess.run(
        argv,
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    prefix = f"[sandbox:{chosen}] " if chosen != "none" else ""
    return SandboxRunResult(
        backend=chosen,
        returncode=proc.returncode,
        stdout=prefix + (proc.stdout or ""),
        stderr=proc.stderr or "",
    )
