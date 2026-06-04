from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from nimbusware_env.desktop_common import (
    default_install_script_args,
    pick_webview_gui,
    poetry_venv_python,
    read_poetry_version,
    repo_root,
    resolve_python_command,
    run_log_path,
    venv_python_candidates,
)
from nimbusware_env.run_app import _reject_legacy_ui_backend


def test_read_poetry_version_from_repo() -> None:
    root = repo_root(start=Path(__file__).resolve().parent)
    version = read_poetry_version(root)
    assert version == "0.5.0"


def test_default_install_script_args_non_interactive() -> None:
    args = default_install_script_args()
    assert "--non-interactive" in args
    assert "--seed-config" in args
    assert "--postgres-choice" in args


def test_pick_webview_gui_for_platform() -> None:
    gui = pick_webview_gui()
    if sys.platform == "win32":
        assert gui == "edgechromium"
    elif sys.platform == "darwin":
        assert gui == "cocoa"
    elif sys.platform.startswith("linux"):
        assert gui == "gtk"
    else:
        assert gui is None


def test_venv_python_candidates_include_platform_paths() -> None:
    root = repo_root(start=Path(__file__).resolve().parent)
    paths = venv_python_candidates(root)
    assert paths
    if sys.platform == "win32":
        assert any("Scripts" in str(p) for p in paths)
    else:
        assert all("bin" in str(p) for p in paths)


def test_resolve_python_command_returns_executable() -> None:
    root = repo_root(start=Path(__file__).resolve().parent)
    cmd = resolve_python_command(root)
    assert cmd
    exe = Path(cmd[0]).name.lower()
    assert exe.startswith("python") or "poetry" in exe
    assert "nimbuswarelauncher" not in exe


def test_poetry_venv_python_when_poetry_available() -> None:
    root = repo_root(start=Path(__file__).resolve().parent)
    if shutil.which("poetry") is None:
        pytest.skip("poetry not on PATH")
    py = poetry_venv_python(root)
    assert py is not None
    assert py.is_file()


def test_run_log_path_under_cache() -> None:
    root = repo_root(start=Path(__file__).resolve().parent)
    path = run_log_path(root)
    assert path.parent.name == ".cache"
    assert path.name == "nimbusware-run.log"


def test_legacy_streamlit_ui_backend_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_UI_BACKEND", "streamlit")
    with pytest.raises(RuntimeError, match="Streamlit retired"):
        _reject_legacy_ui_backend()


def test_resolve_ui_mode_defaults_to_maker(monkeypatch: pytest.MonkeyPatch) -> None:
    from nimbusware_env.run_app import _resolve_ui_mode

    monkeypatch.delenv("NIMBUSWARE_UI", raising=False)
    assert _resolve_ui_mode() == "maker"
    assert _resolve_ui_mode(ui="console") == "admin"
    assert _resolve_ui_mode(ui="admin") == "admin"
    monkeypatch.setenv("NIMBUSWARE_UI", "operator")
    assert _resolve_ui_mode() == "admin"


def test_launcher_module_imports() -> None:
    from nimbusware_env import launcher_app

    assert callable(launcher_app.main)


def test_linux_desktop_deps_skipped_off_linux() -> None:
    from nimbusware_env.linux_desktop_deps import ensure_linux_desktop_deps

    root = repo_root(start=Path(__file__).resolve().parent)
    ok, msg = ensure_linux_desktop_deps(root, [sys.executable])
    if sys.platform.startswith("linux"):
        assert ok or "sudo" in msg.lower() or "manual" in msg.lower()
    else:
        assert ok
        assert "skipped" in msg.lower()


def test_linux_desktop_system_packages_apt() -> None:
    from nimbusware_env.linux_desktop_deps import linux_desktop_system_packages

    pkgs = linux_desktop_system_packages("apt")
    assert "python3-gi" in pkgs
    assert "gir1.2-gtk-3.0" in pkgs


def test_linux_desktop_manual_hint_non_empty() -> None:
    from nimbusware_env.linux_desktop_deps import linux_desktop_manual_hint

    hint = linux_desktop_manual_hint()
    assert hint
