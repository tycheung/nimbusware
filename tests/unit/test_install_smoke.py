from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "install_nimbusware.py"


def test_install_check_only_passes() -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--check-only"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Prerequisite check passed" in proc.stdout


def test_install_help_documents_ollama_flags() -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--help"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "--skip-ollama" in proc.stdout
    assert "--install-ollama" in proc.stdout
    assert "--install-profile" in proc.stdout


def test_install_consumer_plan_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--consumer-plan"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "curl" in proc.stdout.lower()
    assert "install-profile" in proc.stdout
    assert "raw.githubusercontent.com" in proc.stdout
    assert "scripts/install/install_nimbusware.py" in proc.stdout
    assert ".git/raw/" not in proc.stdout


def test_install_print_one_command_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), "--print-one-command"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "One-command install" in proc.stdout


def test_install_script_resolves_repo_from_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib.util

    script_path = (
        Path(__file__).resolve().parents[2] / "scripts" / "install" / "install_nimbusware.py"
    )
    spec = importlib.util.spec_from_file_location("install_nimbusware", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    assert mod._resolve_repo_root() == tmp_path.resolve()
