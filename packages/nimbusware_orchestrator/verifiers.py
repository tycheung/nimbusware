from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from nimbusware_env.env_flags import nimbusware_run_bandit_enabled, nimbusware_run_mypy_enabled


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


def run_pytest_targets(
    workspace: Path,
    targets: list[str],
    *,
    timeout_seconds: float = 120.0,
) -> tuple[int, str]:
    """Run pytest against explicit paths (micro-slice scoped tests)."""
    if not targets:
        return run_pytest(workspace, timeout_seconds=timeout_seconds)
    args = ["pytest", "-q", "--maxfail=1", *targets]
    proc = subprocess.run(
        args,
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


def run_ruff_on_paths(
    workspace: Path,
    paths: list[str],
    *,
    timeout_seconds: float = 60.0,
) -> tuple[int, str]:
    if not paths:
        return 0, "ruff skipped (no paths)\n"
    resolved = []
    for p in paths:
        candidate = workspace / p
        if candidate.is_file():
            resolved.append(str(candidate))
    if not resolved:
        return 0, "ruff skipped (no existing files)\n"
    proc = subprocess.run(
        ["ruff", "check", *resolved],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_mypy(workspace: Path, *, timeout_seconds: float = 120.0) -> tuple[int, str]:
    if not nimbusware_run_mypy_enabled():
        return 0, "mypy skipped (set NIMBUSWARE_RUN_MYPY=1 to enable)\n"
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
    if not nimbusware_run_bandit_enabled():
        return 0, "bandit skipped (set NIMBUSWARE_RUN_BANDIT=1 to enable)\n"
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
