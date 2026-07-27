from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from env.desktop_common import NIMBUSWARE_SCHEMA_REL
from env.launcher_fetch import (
    INSTALL_PROFILE_BAREBONES,
    INSTALL_PROFILE_FULL,
    SETUP_BUNDLE_DEFAULT,
    SETUP_BUNDLE_ENTERPRISE,
)
from env.launcher_manage import (
    UninstallResult,
    read_install_state,
    uninstall_nimbusware,
)

# Install forms the single Uninstall button can face (profile × bundle).
UNINSTALL_FORMS: list[dict[str, Any]] = [
    {
        "id": "quick_individual",
        "profile": INSTALL_PROFILE_BAREBONES,
        "bundle": SETUP_BUNDLE_DEFAULT,
        "edition": "individual",
    },
    {
        "id": "full_individual",
        "profile": INSTALL_PROFILE_FULL,
        "bundle": SETUP_BUNDLE_DEFAULT,
        "edition": "individual",
        "database_url": "postgresql://nimbusware:nimbusware@127.0.0.1:5432/nimbusware",
    },
    {
        "id": "full_enterprise",
        "profile": INSTALL_PROFILE_FULL,
        "bundle": SETUP_BUNDLE_ENTERPRISE,
        "edition": "enterprise",
        "database_url": "postgresql://nimbusware:nimbusware@127.0.0.1:5432/nimbusware",
    },
    {
        "id": "quick_enterprise_bundle_only",
        "profile": INSTALL_PROFILE_BAREBONES,
        "bundle": SETUP_BUNDLE_ENTERPRISE,
        "edition": "enterprise",
    },
]


def _write_checkout(repo: Path, *, with_venv: bool = True) -> None:
    (repo / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "nimbusware"\nversion = "0.0.0"\n',
        encoding="utf-8",
    )
    schema = repo / NIMBUSWARE_SCHEMA_REL
    schema.parent.mkdir(parents=True, exist_ok=True)
    schema.write_text("-- schema\n", encoding="utf-8")
    if with_venv:
        venv = repo / ".venv"
        (venv / "Scripts").mkdir(parents=True)
        (venv / "Scripts" / "python.exe").write_bytes(b"fake")
        (venv / "pyvenv.cfg").write_text("home = /\n", encoding="utf-8")


def _write_env(repo: Path, form: dict[str, Any]) -> Path:
    lines = [
        f"NIMBUSWARE_INSTALL_PROFILE={form['profile']}",
        f"NIMBUSWARE_SETUP_BUNDLE={form['bundle']}",
        f"NIMBUSWARE_EDITION={form['edition']}",
        "NIMBUSWARE_BROKER_HTTP=http://127.0.0.1:8787",
    ]
    db = form.get("database_url")
    if db:
        lines.append(f"NIMBUSWARE_DATABASE_URL={db}")
    path = repo / ".env"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("form", UNINSTALL_FORMS, ids=lambda f: f["id"])
def test_uninstall_removes_venv_preserves_env_for_each_form(
    tmp_path: Path,
    form: dict[str, Any],
) -> None:
    """Single Uninstall button: same cleanup for every Quick/Full/Enterprise form."""
    _write_checkout(tmp_path, with_venv=True)
    env_path = _write_env(tmp_path, form)
    before = env_path.read_text(encoding="utf-8")
    logs: list[str] = []

    with patch("env.launcher_manage.shutil.which", return_value=None):
        result = uninstall_nimbusware(tmp_path, log=logs.append)

    assert isinstance(result, UninstallResult)
    assert result.removed_venv is True
    assert result.ran_poetry_env_remove is False
    assert not (tmp_path / ".venv").exists()
    assert env_path.read_text(encoding="utf-8") == before
    state = read_install_state(tmp_path)
    assert state.install_profile == form["profile"]
    assert state.setup_bundle == form["bundle"]
    assert state.edition == form["edition"]
    if form.get("database_url"):
        assert state.database_url == form["database_url"]
    assert any("Removing virtualenv" in line for line in logs)
    assert any("User data preserved" in line for line in logs)


@pytest.mark.parametrize("form", UNINSTALL_FORMS, ids=lambda f: f["id"])
def test_uninstall_idempotent_without_venv(
    tmp_path: Path,
    form: dict[str, Any],
) -> None:
    """Already-clean tree (no .venv) still succeeds for every install form."""
    _write_checkout(tmp_path, with_venv=False)
    _write_env(tmp_path, form)
    logs: list[str] = []

    with patch("env.launcher_manage.shutil.which", return_value=None):
        result = uninstall_nimbusware(tmp_path, log=logs.append)

    assert result.removed_venv is False
    assert result.ran_poetry_env_remove is False
    assert (tmp_path / ".env").is_file()
    assert any("Uninstall complete" in line for line in logs)


@pytest.mark.parametrize("form", UNINSTALL_FORMS, ids=lambda f: f["id"])
def test_uninstall_runs_poetry_env_remove_when_available(
    tmp_path: Path,
    form: dict[str, Any],
) -> None:
    _write_checkout(tmp_path, with_venv=True)
    _write_env(tmp_path, form)
    calls: list[list[str]] = []

    def _fake_run(cmd: list[str], **kwargs: Any) -> MagicMock:
        calls.append(list(cmd))
        result = MagicMock()
        result.returncode = 0
        return result

    with (
        patch("env.launcher_manage.shutil.which", return_value="C:/Poetry/poetry.exe"),
        patch("env.launcher_manage.subprocess.run", side_effect=_fake_run),
    ):
        result = uninstall_nimbusware(tmp_path)

    assert result.removed_venv is True
    assert result.ran_poetry_env_remove is True
    assert calls, "expected poetry env remove"
    assert calls[0][:3] == ["C:/Poetry/poetry.exe", "env", "remove"]
    assert "--all" in calls[0]
    assert not (tmp_path / ".venv").exists()
    assert (tmp_path / ".env").is_file()


def test_uninstall_skips_poetry_without_pyproject(tmp_path: Path) -> None:
    """Checkout-shaped tree without pyproject must not invoke poetry."""
    schema = tmp_path / NIMBUSWARE_SCHEMA_REL
    schema.parent.mkdir(parents=True, exist_ok=True)
    schema.write_text("-- schema\n", encoding="utf-8")
    venv = tmp_path / ".venv" / "bin"
    venv.mkdir(parents=True)
    (venv / "python").write_text("#!/bin/sh\n", encoding="utf-8")
    _write_env(tmp_path, UNINSTALL_FORMS[0])

    with (
        patch("env.launcher_manage.shutil.which", return_value="C:/Poetry/poetry.exe"),
        patch("env.launcher_manage.subprocess.run") as run_mock,
    ):
        result = uninstall_nimbusware(tmp_path)

    assert result.removed_venv is True
    assert result.ran_poetry_env_remove is False
    run_mock.assert_not_called()


def test_uninstall_raises_when_venv_locked(tmp_path: Path) -> None:
    _write_checkout(tmp_path, with_venv=True)
    _write_env(tmp_path, UNINSTALL_FORMS[1])

    with patch(
        "env.launcher_manage.shutil.rmtree",
        side_effect=OSError(5, "Access is denied"),
    ):
        with pytest.raises(OSError, match="Could not remove virtualenv"):
            uninstall_nimbusware(tmp_path)

    assert (tmp_path / ".venv").is_dir()
    assert (tmp_path / ".env").is_file()


def test_uninstall_raises_when_venv_still_present(tmp_path: Path) -> None:
    _write_checkout(tmp_path, with_venv=True)

    def _noop_rmtree(path: Path | str, *args: Any, **kwargs: Any) -> None:
        return None

    with patch("env.launcher_manage.shutil.rmtree", side_effect=_noop_rmtree):
        with pytest.raises(OSError, match="still present"):
            uninstall_nimbusware(tmp_path)


def test_run_uninstall_no_checkout_shows_error(tmp_path: Path) -> None:
    from env.launcher_app import NimbuswareLauncherApp

    app = MagicMock(spec=NimbuswareLauncherApp)
    app.repo = tmp_path
    with (
        patch("env.launcher_app.is_nimbusware_checkout", return_value=False),
        patch("env.launcher_app.messagebox") as mb,
    ):
        NimbuswareLauncherApp.run_uninstall(app)
    mb.showerror.assert_called_once()
    mb.askyesno.assert_not_called()


def test_run_uninstall_cancel_does_not_remove(tmp_path: Path) -> None:
    from env.launcher_app import NimbuswareLauncherApp

    _write_checkout(tmp_path, with_venv=True)
    app = MagicMock(spec=NimbuswareLauncherApp)
    app.repo = tmp_path
    app._busy = False
    with (
        patch("env.launcher_app.is_nimbusware_checkout", return_value=True),
        patch("env.launcher_app.messagebox") as mb,
        patch("env.launcher_app.uninstall_nimbusware") as uninstall,
    ):
        mb.askyesno.return_value = False
        NimbuswareLauncherApp.run_uninstall(app)
    uninstall.assert_not_called()
    mb.showinfo.assert_not_called()


def test_run_uninstall_confirm_invokes_worker(tmp_path: Path) -> None:
    from env.launcher_app import NimbuswareLauncherApp

    _write_checkout(tmp_path, with_venv=True)
    app = MagicMock(spec=NimbuswareLauncherApp)
    app.repo = tmp_path
    app._busy = False
    app.root = MagicMock()
    workers: list[Any] = []

    def _capture_background(label: str, worker: Any) -> None:
        workers.append((label, worker))

    app._run_background.side_effect = _capture_background
    with (
        patch("env.launcher_app.is_nimbusware_checkout", return_value=True),
        patch("env.launcher_app.messagebox") as mb,
        patch("env.launcher_app.uninstall_nimbusware") as uninstall,
    ):
        mb.askyesno.return_value = True
        NimbuswareLauncherApp.run_uninstall(app)
        assert workers and workers[0][0] == "Uninstalling..."
        workers[0][1]()
        assert app.root.after.called
        done = app.root.after.call_args_list[-1][0][1]
        done()
    uninstall.assert_called_once()
    mb.showinfo.assert_called_once()
    app._sync_repo_ui.assert_called_once()
