"""Clone / update SwissArmyNoife next to a Nimbusware checkout."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from env.desktop_common import (
    check_for_updates,
    git_pull,
    git_subprocess_kwargs,
    is_git_checkout,
    resolve_git_executable,
    run_git,
)
from env.env_flags import env_str

DEFAULT_SWISSARMYNOIFE_CLONE_URL = "https://github.com/tycheung/SwissArmyNoife.git"
DEFAULT_BROKER_HTTP = "http://127.0.0.1:8787"


def swissarmynoife_clone_url(
    default: str = DEFAULT_SWISSARMYNOIFE_CLONE_URL,
) -> str:
    for key in ("SWISSARMYNOIFE_CLONE_URL", "NIMBUSWARE_SAK_CLONE_URL"):
        raw = env_str(key, default="").strip()
        if raw:
            return raw
    return default


def is_swissarmynoife_checkout(root: Path) -> bool:
    return (root / "Cargo.toml").is_file() and (root / "crates" / "mcp").is_dir()


def default_swissarmynoife_target(nimbusware_root: Path) -> Path:
    """Sibling ``SwissArmyNoife/`` next to the Nimbusware repo (Agentic layout)."""
    configured = env_str("NIMBUSWARE_SWISSARMYNOIFE_DIR", default="").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (nimbusware_root.resolve().parent / "SwissArmyNoife").resolve()


def resolve_cargo_executable() -> str | None:
    for env_key in ("CARGO_EXECUTABLE", "NIMBUSWARE_CARGO_EXECUTABLE"):
        configured = os.environ.get(env_key, "").strip()
        if configured and Path(configured).is_file():
            return configured
    return shutil.which("cargo")


def clone_swissarmynoife_repo(
    url: str,
    target: Path,
    *,
    log: Callable[[str], None] | None = None,
) -> Path:
    if target.exists() and any(target.iterdir()):
        if not is_swissarmynoife_checkout(target):
            raise FileNotFoundError(
                f"Target exists but is not a SwissArmyNoife checkout: {target}",
            )
        if log:
            log(f"Using existing SwissArmyNoife checkout at {target}")
        return target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if log:
        log(f"Cloning SwissArmyNoife into {target}...")
    proc = run_git(target.parent, "clone", url, str(target), log=log)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(err or f"git clone SwissArmyNoife failed (exit {proc.returncode})")
    if not is_swissarmynoife_checkout(target):
        raise RuntimeError(f"Cloned tree does not look like SwissArmyNoife: {target}")
    return target.resolve()


def _github_archive_url(repo_url: str, *, branch: str = "main") -> str:
    parsed = urlparse(repo_url.rstrip("/"))
    if parsed.netloc != "github.com":
        raise ValueError(f"archive download supports github.com URLs only: {repo_url}")
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"invalid GitHub repo URL: {repo_url}")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    return f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"


def download_swissarmynoife_archive(
    repo_url: str,
    target: Path,
    *,
    branch: str = "main",
    log: Callable[[str], None] | None = None,
) -> Path:
    import io
    import urllib.request
    import zipfile

    if target.exists() and is_swissarmynoife_checkout(target):
        if log:
            log(f"Using existing SwissArmyNoife checkout at {target}")
        return target.resolve()
    url = _github_archive_url(repo_url, branch=branch)
    if log:
        log(f"Downloading SwissArmyNoife archive: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "NimbuswareLauncher/1.0"})
    with urllib.request.urlopen(request, timeout=180) as response:
        data = response.read()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if not names:
            raise RuntimeError("SwissArmyNoife archive is empty")
        top = names[0].split("/")[0]
        if target.exists():
            raise FileExistsError(f"target exists and is not a SwissArmyNoife checkout: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = target.parent / f".{target.name}-staging"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        try:
            archive.extractall(staging)
            extracted = staging / top
            if not extracted.is_dir():
                raise RuntimeError("unexpected SwissArmyNoife archive layout")
            extracted.rename(target)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
    if not is_swissarmynoife_checkout(target):
        raise RuntimeError(f"extracted tree does not look like SwissArmyNoife: {target}")
    return target.resolve()


def fetch_swissarmynoife_source(
    target: Path,
    *,
    repo_url: str | None = None,
    branch: str = "main",
    log: Callable[[str], None] | None = None,
) -> Path:
    url = repo_url or swissarmynoife_clone_url()
    if target.exists() and is_swissarmynoife_checkout(target):
        if log:
            log(f"Using existing SwissArmyNoife checkout at {target}")
        return target.resolve()
    if resolve_git_executable() is not None:
        return clone_swissarmynoife_repo(url, target, log=log)
    if log:
        log("git not found; falling back to SwissArmyNoife GitHub archive")
    return download_swissarmynoife_archive(url, target, branch=branch, log=log)


def update_swissarmynoife_checkout(
    root: Path,
    *,
    log: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """``git pull --ff-only`` when the broker tree is a git checkout."""
    if not is_swissarmynoife_checkout(root):
        return False, f"not a SwissArmyNoife checkout: {root}"
    if not is_git_checkout(root) or resolve_git_executable() is None:
        return True, "SwissArmyNoife present (archive install — skip git pull)"
    status, available, detail = check_for_updates(root, fetch=True)
    if log:
        log(f"SwissArmyNoife updates: {detail}")
    if not available and status == "up to date":
        return True, detail
    if not available:
        return True, detail
    return git_pull(root, log=log)


def build_swissarmynoife_binaries(
    root: Path,
    *,
    log: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """Build MCP + HTTP admin when ``cargo`` is available."""
    cargo = resolve_cargo_executable()
    if not cargo:
        return False, "cargo not on PATH — skip SwissArmyNoife build (install Rust via rustup)"
    packages = ("mcp", "http-admin")
    for pkg in packages:
        cmd = [cargo, "build", "-p", pkg]
        if log:
            log(f"$ {' '.join(cmd)}")
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
            **git_subprocess_kwargs(),
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            return False, err or f"cargo build -p {pkg} failed (exit {proc.returncode})"
    return True, "built mcp + http-admin"


def ensure_swissarmynoife(
    nimbusware_root: Path,
    *,
    target: Path | None = None,
    skip_build: bool = False,
    log: Callable[[str], None] | None = None,
) -> Path:
    """Fetch or update SwissArmyNoife beside Nimbusware; optionally cargo-build."""
    dest = (target or default_swissarmynoife_target(nimbusware_root)).resolve()
    if dest.exists() and is_swissarmynoife_checkout(dest):
        ok, message = update_swissarmynoife_checkout(dest, log=log)
        if log:
            log(message if ok else f"SwissArmyNoife update warning: {message}")
    else:
        fetch_swissarmynoife_source(dest, log=log)
    if not skip_build:
        built, detail = build_swissarmynoife_binaries(dest, log=log)
        if log:
            log(f"SwissArmyNoife build: {detail}" if built else f"SwissArmyNoife build skipped: {detail}")
    return dest


def write_broker_env(nimbusware_root: Path, *, broker_http: str = DEFAULT_BROKER_HTTP) -> Path:
    """Persist default broker HTTP URL when unset."""
    from env.dotenv import set_env_var

    existing = env_str("NIMBUSWARE_BROKER_HTTP", default="").strip()
    if existing:
        return nimbusware_root / ".env"
    return set_env_var("NIMBUSWARE_BROKER_HTTP", broker_http, repo_root=nimbusware_root)
