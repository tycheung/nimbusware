"""Shared helpers for Nimbusware desktop launcher and run entry points."""

from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from nimbusware_env.dotenv import find_repo_root

NIMBUSWARE_SCHEMA_REL = Path("packages/nimbusware_store/schema/postgres.sql")
DEFAULT_CLONE_URL = "https://github.com/tycheung/nimbusware.git"


def repo_root(*, start: Path | None = None) -> Path:
    """Nimbusware repo root; when frozen, resolve from the executable directory."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        for candidate in (exe_dir, exe_dir / "Nimbusware"):
            if (candidate / "pyproject.toml").is_file():
                return candidate
        return exe_dir
    return find_repo_root(start=start or Path.cwd())


def is_nimbusware_checkout(root: Path) -> bool:
    """True when ``root`` looks like an installed Nimbusware tree."""
    return (root / "pyproject.toml").is_file() and (root / NIMBUSWARE_SCHEMA_REL).is_file()


def is_git_checkout(root: Path) -> bool:
    return (root / ".git").is_dir()


def default_clone_url() -> str:
    return os.environ.get("NIMBUSWARE_CLONE_URL", DEFAULT_CLONE_URL)


def default_clone_target(base: Path) -> Path:
    """Directory used when the launcher clones Nimbusware next to itself."""
    if is_nimbusware_checkout(base):
        return base
    return base / "Nimbusware"


def resolve_git_executable() -> str | None:
    """Return a Git executable path that works from GUI apps on Windows."""
    for env_key in ("NIMBUSWARE_GIT_EXECUTABLE", "GIT_EXECUTABLE"):
        configured = os.environ.get(env_key, "").strip()
        if configured and Path(configured).is_file():
            return configured
    if sys.platform == "win32":
        for program_files in (
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        ):
            candidate = Path(program_files) / "Git" / "mingw64" / "bin" / "git.exe"
            if candidate.is_file():
                return str(candidate)
    return shutil.which("git")


def git_subprocess_kwargs() -> dict[str, object]:
    """Extra ``Popen`` / ``run`` kwargs for headless git invocations."""
    kwargs: dict[str, object] = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return kwargs


def run_git(
    root: Path,
    *git_args: str,
    log: Callable[[str], None] | None = None,
) -> subprocess.CompletedProcess[str]:
    git = resolve_git_executable()
    if not git:
        raise FileNotFoundError("git is not installed or not on PATH.")
    cmd = [git, *git_args]
    if log:
        log(f"$ {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        **git_subprocess_kwargs(),
    )


def clone_nimbusware_repo(
    url: str,
    target: Path,
    *,
    log: Callable[[str], None] | None = None,
) -> Path:
    """Clone Nimbusware into ``target`` (or reuse an existing checkout)."""
    if target.exists() and any(target.iterdir()):
        if not is_nimbusware_checkout(target):
            raise FileNotFoundError(f"Target exists but is not a Nimbusware checkout: {target}")
        if log:
            log(f"Using existing checkout at {target}")
        return target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    proc = run_git(target.parent, "clone", url, str(target), log=log)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(err or f"git clone failed (exit {proc.returncode})")
    if not is_nimbusware_checkout(target):
        raise RuntimeError(f"Cloned repo does not look like Nimbusware: {target}")
    return target.resolve()


def updates_supported(root: Path) -> bool:
    return is_git_checkout(root) and resolve_git_executable() is not None


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


def python_in_venv(venv_root: Path) -> Path | None:
    """Return the interpreter inside a Poetry/virtualenv root directory."""
    if sys.platform == "win32":
        candidates = (
            venv_root / "Scripts" / "python.exe",
            venv_root / "Scripts" / "python3.exe",
        )
    else:
        candidates = (
            venv_root / "bin" / "python3",
            venv_root / "bin" / "python",
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def poetry_venv_python(root: Path) -> Path | None:
    """Resolve ``poetry env info -p`` when Poetry manages the project venv."""
    poetry = shutil.which("poetry")
    if not poetry:
        return None
    proc = subprocess.run(
        [poetry, "env", "info", "-p"],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return python_in_venv(Path(proc.stdout.strip()))


def resolve_python_command(root: Path) -> list[str]:
    """Prefer repo ``.venv``, then Poetry's env, then ``poetry run python``.

    Never use a frozen launcher executable as Python.
    """
    for candidate in venv_python_candidates(root):
        if candidate.is_file():
            return [str(candidate)]
    poetry_python = poetry_venv_python(root)
    if poetry_python is not None:
        return [str(poetry_python)]
    poetry = shutil.which("poetry")
    if poetry:
        return [poetry, "run", "python"]
    if getattr(sys, "frozen", False):
        raise FileNotFoundError(
            "No Python environment found for this repo. "
            "Use Install / setup in the launcher (or run scripts/install_nimbusware.py)."
        )
    return [sys.executable]


def run_log_path(root: Path) -> Path:
    """Desktop run diagnostics log (API / web UI / pywebview startup)."""
    log_dir = root / ".cache"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "nimbusware-run.log"


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


def subprocess_spawn_kwargs(
    *,
    detach: bool = False,
    hide_window: bool = False,
) -> dict[str, object]:
    """Extra ``Popen`` kwargs.

    Use ``hide_window=True`` for headless API children on Windows.
    Leave it false when starting ``run.py`` so failures can surface a console.
    """
    kwargs: dict[str, object] = {}
    if sys.platform == "win32" and hide_window:
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    elif detach and sys.platform != "win32":
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
    merged.setdefault("NIMBUSWARE_REPO_ROOT", str(root))
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
    proc = run_git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if proc.returncode != 0 or not proc.stdout.strip():
        proc = run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
        branch = proc.stdout.strip() if proc.returncode == 0 else "main"
        return f"origin/{branch}" if branch else None
    ref = proc.stdout.strip()
    if ref.startswith("origin/"):
        return ref
    return ref.replace("refs/remotes/", "")


def check_for_updates(root: Path, *, fetch: bool = True) -> tuple[str, bool, str]:
    """Return ``(status_label, updates_available, detail_message)``."""
    if not is_git_checkout(root):
        return ("not a git repo", False, "Updates require a git checkout with a remote.")
    if resolve_git_executable() is None:
        return ("git missing", False, "Install git to check for updates.")

    if fetch:
        fetch_proc = run_git(root, "fetch", "--quiet", "origin")
        if fetch_proc.returncode != 0:
            err = (fetch_proc.stderr or fetch_proc.stdout or "").strip()
            return ("fetch failed", False, err or "git fetch origin failed")

    upstream = git_remote_branch(root)
    if not upstream:
        return ("no upstream", False, "Could not determine upstream branch.")

    behind_proc = run_git(root, "rev-list", "--count", f"HEAD..{upstream}")
    ahead_proc = run_git(root, "rev-list", "--count", f"{upstream}..HEAD")
    if behind_proc.returncode != 0:
        return ("upstream missing", False, f"Upstream {upstream} not found. Push or set remote.")

    behind = int((behind_proc.stdout or "0").strip() or "0")
    ahead = int((ahead_proc.stdout or "0").strip() or "0")
    local = run_git(root, "rev-parse", "--short", "HEAD")
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
    proc = run_git(root, "pull", "--ff-only", log=log)
    out = (proc.stdout or "") + (proc.stderr or "")
    if log and out.strip():
        for line in out.strip().splitlines():
            log(line)
    if proc.returncode != 0:
        return False, out.strip() or "git pull failed"
    return True, out.strip() or "Updated successfully."
