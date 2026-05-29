"""Shared helpers for Hermes desktop launcher and run entry points."""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from hermes_env.dotenv import find_repo_root


def repo_root(*, start: Path | None = None) -> Path:
    """Hermes repo root; when frozen, search from the executable directory first."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        for candidate in (exe_dir, *exe_dir.parents):
            if (candidate / "pyproject.toml").is_file():
                return candidate
    return find_repo_root(start=start or Path.cwd())


def venv_python_candidates(root: Path) -> tuple[Path, ...]:
    """Platform-specific paths to the repo virtualenv interpreter."""
    if sys.platform == "win32":
        return (
            root / ".venv" / "Scripts" / "python.exe",
            root / ".venv" / "Scripts" / "python3.exe",
            root / ".venv" / "bin" / "python",
            root / ".venv" / "bin" / "python3",
        )
    return (
        root / ".venv" / "bin" / "python3",
        root / ".venv" / "bin" / "python",
    )


def resolve_python_command(root: Path) -> list[str]:
    """Prefer repo ``.venv`` Python, then ``poetry run python``, then current interpreter."""
    for candidate in venv_python_candidates(root):
        if candidate.is_file():
            return [str(candidate)]
    poetry = shutil.which("poetry")
    if poetry:
        return [poetry, "run", "python"]
    return [sys.executable]


def default_install_script_args() -> list[str]:
    """Non-interactive install flags; Docker Postgres when the install script supports it."""
    return ["--non-interactive", "--seed-config", "--postgres-choice", "docker"]


def pick_webview_gui() -> str | None:
    """Select a native pywebview backend for the current platform."""
    if sys.platform == "win32":
        return "edgechromium"
    if sys.platform == "darwin":
        return "cocoa"
    if sys.platform.startswith("linux"):
        return "gtk"
    return None


def ui_title_font() -> tuple[str, int, str]:
    if sys.platform == "win32":
        return ("Segoe UI", 16, "bold")
    if sys.platform == "darwin":
        return ("Helvetica", 16, "bold")
    return ("DejaVu Sans", 15, "bold")


def ui_mono_font() -> tuple[str, int]:
    if sys.platform == "win32":
        return ("Consolas", 10)
    if sys.platform == "darwin":
        return ("Menlo", 11)
    return ("DejaVu Sans Mono", 10)


def subprocess_spawn_kwargs(*, detach: bool = False) -> dict[str, object]:
    """Extra ``Popen`` kwargs for background services (API / Streamlit)."""
    kwargs: dict[str, object] = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    elif detach:
        kwargs["start_new_session"] = True
    return kwargs


def terminate_process(proc: subprocess.Popen[object]) -> None:
    """Terminate a child process (and its group on Unix when in a new session)."""
    if proc.poll() is not None:
        return
    if sys.platform != "win32":
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            return
        except (ProcessLookupError, PermissionError, OSError):
            pass
    proc.terminate()


def read_poetry_version(root: Path) -> str:
    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        return "unknown"
    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else "unknown"


def run_script(
    root: Path,
    script_rel: str,
    *script_args: str,
    env: dict[str, str] | None = None,
    log: Callable[[str], None] | None = None,
) -> int:
    script = root / script_rel
    if not script.is_file():
        raise FileNotFoundError(f"Missing script: {script}")
    cmd = [*resolve_python_command(root), str(script), *script_args]
    if log:
        log(f"$ {' '.join(cmd)}")
    merged = os.environ.copy()
    merged.setdefault("HERMES_REPO_ROOT", str(root))
    if env:
        merged.update(env)
    proc = subprocess.run(
        cmd,
        cwd=str(root),
        env=merged,
        text=True,
    )
    return proc.returncode


def git_remote_branch(root: Path) -> str | None:
    proc = subprocess.run(
        ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        branch = proc.stdout.strip() if proc.returncode == 0 else "main"
        return f"origin/{branch}" if branch else None
    ref = proc.stdout.strip()
    if ref.startswith("origin/"):
        return ref
    return ref.replace("refs/remotes/", "")


def check_for_updates(root: Path, *, fetch: bool = True) -> tuple[str, bool, str]:
    """Return ``(status_label, updates_available, detail_message)``."""
    if not (root / ".git").is_dir():
        return ("not a git repo", False, "Updates require a git checkout with a remote.")
    if shutil.which("git") is None:
        return ("git missing", False, "Install git to check for updates.")

    if fetch:
        fetch_proc = subprocess.run(
            ["git", "fetch", "--quiet", "origin"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if fetch_proc.returncode != 0:
            err = (fetch_proc.stderr or fetch_proc.stdout or "").strip()
            return ("fetch failed", False, err or "git fetch origin failed")

    upstream = git_remote_branch(root)
    if not upstream:
        return ("no upstream", False, "Could not determine upstream branch.")

    behind_proc = subprocess.run(
        ["git", "rev-list", "--count", f"HEAD..{upstream}"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    ahead_proc = subprocess.run(
        ["git", "rev-list", "--count", f"{upstream}..HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    if behind_proc.returncode != 0:
        return ("upstream missing", False, f"Upstream {upstream} not found. Push or set remote.")

    behind = int((behind_proc.stdout or "0").strip() or "0")
    ahead = int((ahead_proc.stdout or "0").strip() or "0")
    local = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    local_sha = local.stdout.strip() if local.returncode == 0 else "?"

    if behind > 0:
        detail = f"{behind} commit(s) behind {upstream} (local {local_sha})."
        if ahead:
            detail += f" {ahead} local commit(s) not pushed."
        return ("update available", True, detail)

    detail = f"Up to date with {upstream} ({local_sha})."
    if ahead:
        detail += f" {ahead} local commit(s) ahead of remote."
    return ("up to date", False, detail)


def git_pull(root: Path, *, log: Callable[[str], None] | None = None) -> tuple[bool, str]:
    if log:
        log("$ git pull --ff-only")
    proc = subprocess.run(
        ["git", "pull", "--ff-only"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if log and out.strip():
        for line in out.strip().splitlines():
            log(line)
    if proc.returncode != 0:
        return False, out.strip() or "git pull failed"
    return True, out.strip() or "Updated successfully."
