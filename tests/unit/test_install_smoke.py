from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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


def test_model_hub_and_install_profile_docs_exist() -> None:
    assert (_REPO / "docs" / "model-hub.md").is_file()
    assert (_REPO / "docs" / "install-profiles.md").is_file()
    hub = (_REPO / "docs" / "model-hub.md").read_text(encoding="utf-8")
    assert "provider-connections" in hub
