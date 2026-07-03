from __future__ import annotations

import platform
import sys
from urllib.parse import urlparse


def launcher_platform_slug() -> str:
    system = sys.platform
    machine = platform.machine().lower()
    if system == "win32":
        arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
        return f"windows-{arch}"
    if system == "darwin":
        arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
        return f"macos-{arch}"
    if system.startswith("linux"):
        if machine in {"aarch64", "arm64"}:
            return "linux-arm64"
        if machine in {"x86_64", "amd64"}:
            return "linux-x86_64"
        return f"linux-{machine}"
    return f"{system}-{machine}"


def launcher_asset_filename() -> str:
    base = f"NimbuswareLauncher-{launcher_platform_slug()}"
    if sys.platform == "win32":
        return f"{base}.zip"
    if sys.platform == "darwin":
        return f"{base}.dmg"
    return f"{base}.tar.gz"


def github_repo_parts(repo_url: str) -> tuple[str, str]:
    parsed = urlparse(repo_url.rstrip("/"))
    if parsed.netloc != "github.com":
        raise ValueError(f"github.com repo URL required: {repo_url}")
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"invalid GitHub repo URL: {repo_url}")
    return parts[0], parts[1].removesuffix(".git")


def launcher_release_download_url(repo_url: str, *, tag: str = "latest") -> str:
    owner, repo = github_repo_parts(repo_url)
    filename = launcher_asset_filename()
    if tag == "latest":
        return f"https://github.com/{owner}/{repo}/releases/latest/download/{filename}"
    return f"https://github.com/{owner}/{repo}/releases/download/{tag}/{filename}"
