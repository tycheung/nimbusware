from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from nimbusware_orchestrator.workspace_layout import WorkspaceLayout, detect_workspace_layout


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


def run_go_test(
    workspace: Path,
    *,
    timeout_seconds: float = 120.0,
    package: str = "./...",
) -> tuple[int, str]:
    exe = shutil.which("go")
    if not exe:
        return 0, "go not on PATH; skipped\n"
    proc = subprocess.run(
        [exe, "test", package],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_mvn_test(
    workspace: Path,
    *,
    timeout_seconds: float = 180.0,
    test_selector: str | None = None,
) -> tuple[int, str]:
    exe = shutil.which("mvn")
    if not exe:
        return 0, "mvn not on PATH; skipped\n"
    args = [exe, "-B", "clean", "test"]
    if test_selector:
        args.extend(["-Dtest", test_selector])
    proc = subprocess.run(
        args,
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


def _layout_or_detect(workspace: Path, layout: WorkspaceLayout | None) -> WorkspaceLayout:
    return layout if layout is not None else detect_workspace_layout(workspace)


def run_ruff_check(workspace: Path, *, timeout_seconds: float = 60.0) -> tuple[int, str]:
    layout = detect_workspace_layout(workspace)
    paths = layout.scan_paths()
    if not paths:
        return 0, "ruff skipped (no scan paths)\n"
    proc = subprocess.run(
        ["ruff", "check", *[str(p) for p in paths]],
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
        elif candidate.is_dir():
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


def run_ruff_format_check(
    workspace: Path,
    paths: list[str] | None,
    *,
    timeout_seconds: float = 60.0,
) -> tuple[int, str]:
    layout = detect_workspace_layout(workspace)
    targets = paths if paths else [str(p) for p in layout.scan_paths()]
    if not targets:
        return 0, "ruff format skipped (no targets)\n"
    proc = subprocess.run(
        ["ruff", "format", "--check", *targets],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_mypy(workspace: Path, *, timeout_seconds: float = 120.0) -> tuple[int, str]:
    return run_mypy_on_layout(detect_workspace_layout(workspace), timeout_seconds=timeout_seconds)


def run_mypy_on_layout(
    layout: WorkspaceLayout,
    *,
    timeout_seconds: float = 120.0,
) -> tuple[int, str]:
    from nimbusware_env.env_flags import nimbusware_run_mypy_enabled

    if not nimbusware_run_mypy_enabled() and not layout.has_mypy_config:
        return 0, "mypy skipped (set NIMBUSWARE_RUN_MYPY=1 or add mypy config)\n"
    exe = shutil.which("mypy")
    if not exe:
        return 0, "mypy not on PATH; skipped\n"
    paths = [str(p) for p in layout.scan_paths()]
    if not paths:
        return 0, "mypy skipped (no scan paths)\n"
    proc = subprocess.run(
        [exe, *paths],
        cwd=layout.workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_bandit(workspace: Path, *, timeout_seconds: float = 120.0) -> tuple[int, str]:
    from nimbusware_env.env_flags import nimbusware_run_bandit_enabled

    if not nimbusware_run_bandit_enabled():
        return 0, "bandit skipped (set NIMBUSWARE_RUN_BANDIT=1 to enable)\n"
    return run_bandit_on_layout(detect_workspace_layout(workspace), timeout_seconds=timeout_seconds)


def run_bandit_on_layout(
    layout: WorkspaceLayout,
    *,
    timeout_seconds: float = 120.0,
) -> tuple[int, str]:
    exe = shutil.which("bandit")
    if not exe:
        return 0, "bandit not on PATH; skipped\n"
    paths = [str(p) for p in layout.scan_paths()]
    if not paths:
        return 0, "bandit skipped (no scan paths)\n"
    args = [exe, "-q", "-r", *paths]
    if layout.has_bandit_config and (layout.workspace / "pyproject.toml").is_file():
        args = [exe, "-q", "-c", str(layout.workspace / "pyproject.toml"), "-r", *paths]
    proc = subprocess.run(
        args,
        cwd=layout.workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_pip_audit(workspace: Path, *, timeout_seconds: float = 120.0) -> tuple[int, str]:
    exe = shutil.which("pip-audit")
    if not exe:
        return 1, "pip-audit not on PATH\n"
    layout = detect_workspace_layout(workspace)
    if layout.has_poetry_lock:
        proc = subprocess.run(
            [exe],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    else:
        proc = subprocess.run(
            [exe, "-r", "requirements.txt"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def run_writer_verifier_bundle(workspace: Path) -> tuple[int, str]:
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


VERIFIER_SHARD_NAMES: tuple[str, ...] = ("pytest", "ruff", "bandit")
_VERIFIER_SHARD_RUNNERS = {
    "pytest": run_pytest,
    "ruff": run_ruff_check,
    "bandit": run_bandit,
}


def run_writer_verifier_shard(workspace: Path, shard: str) -> tuple[int, str]:
    fn = _VERIFIER_SHARD_RUNNERS.get(str(shard).strip().lower())
    if fn is None:
        return 1, f"unknown verify shard: {shard}\n"
    return fn(workspace)


def merge_verifier_shard_logs(shards: dict[str, tuple[int, str]]) -> tuple[int, str]:
    sections: list[str] = []
    worst = 0
    for name in VERIFIER_SHARD_NAMES:
        code, out = shards.get(name, (1, f"missing shard {name}"))
        worst = max(worst, code)
        sections.append(f"=== {name} (exit {code}) ===\n{out}")
    return worst, "\n".join(sections)
