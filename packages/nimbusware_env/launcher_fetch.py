from __future__ import annotations

import io
import shutil
import sys
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from nimbusware_env.desktop_common import (
    clone_nimbusware_repo,
    is_nimbusware_checkout,
    resolve_git_executable,
)

INSTALL_PROFILE_BAREBONES = "barebones"
INSTALL_PROFILE_FULL = "recommended"


def install_script_args(profile: str = INSTALL_PROFILE_BAREBONES) -> list[str]:
    if profile == INSTALL_PROFILE_FULL:
        return [
            "--non-interactive",
            "--seed-config",
            "--postgres-choice",
            "docker",
            "--install-profile",
            INSTALL_PROFILE_FULL,
        ]
    return [
        "--non-interactive",
        "--skip-postgres",
        "--install-profile",
        INSTALL_PROFILE_BAREBONES,
    ]


def github_archive_url(repo_url: str, *, branch: str = "main") -> str:
    parsed = urlparse(repo_url.rstrip("/"))
    if parsed.netloc != "github.com":
        raise ValueError(f"archive download supports github.com URLs only: {repo_url}")
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"invalid GitHub repo URL: {repo_url}")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    return f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"


def bundled_install_script() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return None
    candidate = Path(meipass) / "install" / "install_nimbusware.py"
    return candidate if candidate.is_file() else None


def resolve_install_script(root: Path) -> Path:
    repo_script = root / "scripts" / "install" / "install_nimbusware.py"
    if repo_script.is_file():
        return repo_script
    bundled = bundled_install_script()
    if bundled is not None:
        return bundled
    raise FileNotFoundError(
        "install_nimbusware.py not found in checkout or launcher bundle",
    )


def resolve_bootstrap_python(root: Path) -> list[str]:
    if is_nimbusware_checkout(root):
        from nimbusware_env.desktop_common import resolve_python_command

        try:
            return resolve_python_command(root)
        except FileNotFoundError:
            pass
    for name in ("python3", "python", "py"):
        path = shutil.which(name)
        if path:
            if name == "py":
                return [path, "-3"]
            return [path]
    raise FileNotFoundError(
        "Python 3.10+ is required on PATH before Install / setup can run.",
    )


def _extract_github_zip(data: bytes, target: Path, *, log: Callable[[str], None] | None) -> Path:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if not names:
            raise RuntimeError("downloaded archive is empty")
        top = names[0].split("/")[0]
        if target.exists():
            if not is_nimbusware_checkout(target):
                raise FileExistsError(f"target exists and is not a Nimbusware checkout: {target}")
            if log:
                log(f"Using existing checkout at {target}")
            return target.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = target.parent / f".{target.name}-staging"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        archive.extractall(staging)
        extracted = staging / top
        if not extracted.is_dir():
            shutil.rmtree(staging, ignore_errors=True)
            raise RuntimeError("unexpected GitHub archive layout")
        extracted.rename(target)
        shutil.rmtree(staging, ignore_errors=True)
    if not is_nimbusware_checkout(target):
        raise RuntimeError(f"extracted tree does not look like Nimbusware: {target}")
    return target.resolve()


def download_nimbusware_archive(
    repo_url: str,
    target: Path,
    *,
    branch: str = "main",
    log: Callable[[str], None] | None = None,
) -> Path:
    if target.exists() and is_nimbusware_checkout(target):
        if log:
            log(f"Using existing checkout at {target}")
        return target.resolve()
    url = github_archive_url(repo_url, branch=branch)
    if log:
        log(f"Downloading source archive: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "NimbuswareLauncher/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    if log:
        log(f"Extracting into {target}...")
    return _extract_github_zip(data, target, log=log)


def fetch_nimbusware_source(
    repo_url: str,
    target: Path,
    *,
    branch: str = "main",
    log: Callable[[str], None] | None = None,
) -> Path:
    if target.exists() and is_nimbusware_checkout(target):
        if log:
            log(f"Using existing checkout at {target}")
        return target.resolve()
    if resolve_git_executable() is not None:
        if log:
            log(f"Cloning Nimbusware into {target}...")
        return clone_nimbusware_repo(repo_url, target, log=log)
    if log:
        log("git not found; falling back to GitHub source archive download")
    return download_nimbusware_archive(repo_url, target, branch=branch, log=log)


def run_install_script(
    root: Path,
    *,
    profile: str = INSTALL_PROFILE_BAREBONES,
    log: Callable[[str], None] | None = None,
) -> int:
    import os
    import subprocess

    script = resolve_install_script(root)
    cmd = [*resolve_bootstrap_python(root), str(script), *install_script_args(profile)]
    if log:
        log(f"$ {' '.join(cmd)}")
    env = os.environ.copy()
    env.setdefault("NIMBUSWARE_REPO_ROOT", str(root))
    return subprocess.run(cmd, cwd=str(root), env=env, text=True).returncode
