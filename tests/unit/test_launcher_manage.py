from __future__ import annotations

from pathlib import Path

from env.launcher_fetch import INSTALL_PROFILE_BAREBONES, INSTALL_PROFILE_FULL
from env.launcher_manage import (
    InstallState,
    convert_label,
    postgres_extra_args,
    read_env_file,
    read_install_state,
)


def test_read_env_file_missing(tmp_path: Path) -> None:
    assert read_env_file(tmp_path) == {}


def test_read_install_state_defaults(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('version = "0.0.0"\n', encoding="utf-8")
    state = read_install_state(tmp_path)
    assert state.install_profile == INSTALL_PROFILE_BAREBONES
    assert state.setup_bundle == "default"
    assert state.edition == "individual"


def test_read_install_state_from_env(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "NIMBUSWARE_INSTALL_PROFILE=recommended\n"
        "NIMBUSWARE_SETUP_BUNDLE=enterprise\n"
        "NIMBUSWARE_EDITION=enterprise\n"
        "NIMBUSWARE_DATABASE_URL=postgresql://nimbusware:nimbusware@db/nimbusware\n",
        encoding="utf-8",
    )
    state = read_install_state(tmp_path)
    assert state.install_profile == INSTALL_PROFILE_FULL
    assert state.setup_bundle == "enterprise"
    assert state.database_url == "postgresql://nimbusware:nimbusware@db/nimbusware"


def test_postgres_extra_args_from_env(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "NIMBUSWARE_DATABASE_URL=postgresql://nimbusware:nimbusware@db/nimbusware\n"
        "NIMBUSWARE_POSTGRES_ADMIN_URL=postgresql://postgres:pw@db/postgres\n",
        encoding="utf-8",
    )
    extras = postgres_extra_args(tmp_path)
    assert "--database-url" in extras
    assert "--postgres-admin-url" in extras


def test_convert_label() -> None:
    state = InstallState(
        install_profile=INSTALL_PROFILE_BAREBONES,
        setup_bundle="default",
        edition="individual",
        database_url=None,
    )
    assert convert_label(state) == "Quick / Individual"
