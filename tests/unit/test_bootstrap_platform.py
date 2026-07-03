from __future__ import annotations

import sys
from pathlib import Path

import pytest

_PKG = Path(__file__).resolve().parents[2] / "packages" / "bootstrap"
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from bootstrap.platform import (
    github_repo_parts,
    launcher_asset_filename,
    launcher_platform_slug,
    launcher_release_download_url,
)


def test_launcher_platform_slug_non_empty() -> None:
    assert launcher_platform_slug()


def test_launcher_asset_filename_suffix() -> None:
    name = launcher_asset_filename()
    assert name.startswith("NimbuswareLauncher-")


def test_github_repo_parts() -> None:
    owner, repo = github_repo_parts("https://github.com/tycheung/nimbusware.git")
    assert owner == "tycheung"
    assert repo == "nimbusware"


def test_launcher_release_download_url() -> None:
    url = launcher_release_download_url("https://github.com/tycheung/nimbusware.git")
    assert "/releases/latest/download/NimbuswareLauncher-" in url


def test_github_repo_parts_rejects_non_github() -> None:
    with pytest.raises(ValueError, match="github.com"):
        github_repo_parts("https://gitlab.com/a/b")
