from __future__ import annotations

import importlib.util
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "install_nimbusware.py"


def _load_install_module():
    spec = importlib.util.spec_from_file_location("install_nimbusware", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_happy_path_mentions_quick_mode_and_chat(capsys) -> None:
    mod = _load_install_module()
    mod._print_happy_path(_REPO)
    out = capsys.readouterr().out
    assert "nimbusware-run --quick" in out
    assert "#/chat" in out
    assert "tiny_python_app" in out
    assert "Fix a bug" in out


def test_one_command_install_lines_documented(capsys) -> None:
    mod = _load_install_module()
    mod._print_one_command_install(_REPO)
    out = capsys.readouterr().out
    assert "--clone" in out
    assert "--non-interactive" in out
    assert "--skip-postgres" in out
    lines = mod._one_command_install_lines(_REPO)
    assert len(lines) >= 2
    assert all("--non-interactive" in line for line in lines)
