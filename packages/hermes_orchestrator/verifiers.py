"""Deterministic local verifiers (plan §12 Phase 1, §14 #5)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def run_pytest(workspace: Path, *, timeout_seconds: float = 120.0) -> tuple[int, str]:
    proc = subprocess.run(
        ["pytest", "-q"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_ruff_check(workspace: Path, *, timeout_seconds: float = 60.0) -> tuple[int, str]:
    proc = subprocess.run(
        ["ruff", "check", str(workspace / "packages")],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_mypy(workspace: Path, *, timeout_seconds: float = 120.0) -> tuple[int, str]:
    if os.environ.get("HERMES_RUN_MYPY", "").lower() not in ("1", "true", "yes"):
        return 0, "mypy skipped (set HERMES_RUN_MYPY=1 to enable)\n"
    exe = shutil.which("mypy")
    if not exe:
        return 0, "mypy not on PATH; skipped\n"
    proc = subprocess.run(
        [exe, str(workspace / "packages")],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_bandit(workspace: Path, *, timeout_seconds: float = 120.0) -> tuple[int, str]:
    if os.environ.get("HERMES_RUN_BANDIT", "").lower() not in ("1", "true", "yes"):
        return 0, "bandit skipped (set HERMES_RUN_BANDIT=1 to enable)\n"
    exe = shutil.which("bandit")
    if not exe:
        return 0, "bandit not on PATH; skipped\n"
    proc = subprocess.run(
        [exe, "-q", "-r", str(workspace / "packages")],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_writer_verifier_bundle(workspace: Path) -> tuple[int, str]:
    """Run pytest then ruff then bandit; return worst exit code and merged log."""
    sections: list[str] = []
    worst = 0
    for name, fn in (
        ("pytest", run_pytest),
        ("ruff", run_ruff_check),
        ("bandit", run_bandit),
    ):
        code, out = fn(workspace)
        worst = max(worst, code)
        sections.append(f"=== {name} (exit {code}) ===\n{out}")
    return worst, "\n".join(sections)
