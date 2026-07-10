from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from env.launcher_fetch import (
    INSTALL_PROFILE_BAREBONES,
    INSTALL_PROFILE_FULL,
    github_archive_url,
    install_script_args,
    resolve_install_script,
)


def test_install_script_args_barebones() -> None:
    args = install_script_args(INSTALL_PROFILE_BAREBONES)
    assert "--skip-postgres" in args
    assert "--install-profile" in args
    assert args[args.index("--install-profile") + 1] == INSTALL_PROFILE_BAREBONES


def test_install_script_args_full_uses_provided_postgres() -> None:
    args = install_script_args(INSTALL_PROFILE_FULL)
    assert "--postgres-choice" in args
    assert args[args.index("--postgres-choice") + 1] == "provided"
    assert "--skip-docker" in args
    assert "docker" not in args
    assert args[args.index("--install-profile") + 1] == INSTALL_PROFILE_FULL


def test_install_script_args_extra_args() -> None:
    args = install_script_args(
        INSTALL_PROFILE_FULL,
        extra_args=["--database-url", "postgresql://u:p@h/d"],
    )
    assert "--database-url" in args
    assert "postgresql://u:p@h/d" in args


def test_github_archive_url() -> None:
    url = github_archive_url("https://github.com/tycheung/nimbusware.git")
    assert url.endswith("/nimbusware/archive/refs/heads/main.zip")


def test_github_archive_url_rejects_non_github() -> None:
    with pytest.raises(ValueError, match="github.com"):
        github_archive_url("https://gitlab.com/foo/bar")


def test_resolve_install_script_from_repo() -> None:
    root = Path(__file__).resolve().parents[2]
    script = resolve_install_script(root)
    assert script.name == "install_nimbusware.py"
    assert script.is_file()


def test_extract_github_zip_layout(tmp_path: Path) -> None:
    from env.desktop_common import NIMBUSWARE_SCHEMA_REL
    from env.launcher_fetch import _extract_github_zip

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("nimbusware-main/pyproject.toml", 'version = "0.0.0"\n')
        archive.writestr(
            f"nimbusware-main/{NIMBUSWARE_SCHEMA_REL.as_posix()}",
            "-- schema\n",
        )
    target = tmp_path / "ws"
    out = _extract_github_zip(buffer.getvalue(), target, log=None)
    assert out == target.resolve()
    assert (target / "pyproject.toml").is_file()
