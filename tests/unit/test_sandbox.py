from __future__ import annotations

from pathlib import Path

import pytest

from hermes_agent_tools.sandbox import resolve_sandbox_backend, run_subprocess_in_sandbox
from hermes_agent_tools.tools import tool_run_shell


def test_resolve_sandbox_backend_defaults_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERMES_SANDBOX_BACKEND", raising=False)
    assert resolve_sandbox_backend() == "none"


def test_stub_backend_tags_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_SANDBOX_BACKEND", "stub")
    if Path("python").exists() or Path("python3").exists():
        result = tool_run_shell(tmp_path, "python", ["-c", "print('ok')"])
        assert "[sandbox:stub]" in result.output or result.ok


def test_run_subprocess_in_sandbox_none_prefix(tmp_path: Path) -> None:
    proc = run_subprocess_in_sandbox(
        tmp_path,
        ["python", "-c", "print(1)"],
        timeout_seconds=30.0,
        backend="none",
    )
    assert proc.backend == "none"
    assert not proc.stdout.startswith("[sandbox:")
