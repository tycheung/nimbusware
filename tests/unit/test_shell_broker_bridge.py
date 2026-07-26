from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agent_tools.shell_tools import tool_run_shell


def test_tool_run_shell_uses_broker_without_local_sandbox(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker_called: list[tuple[list[str], str]] = []
    sandbox_called: list[object] = []

    def _broker(argv: list[str], cwd: str = ".") -> dict:
        broker_called.append((argv, cwd))
        return {"exit_code": 0, "stdout": "broker ok"}

    def _local_sandbox(*_args, **_kwargs):
        sandbox_called.append(True)
        raise AssertionError("local sandbox should not run when broker succeeds")

    monkeypatch.setattr("agent_tools.sandbox_bridge.try_broker_sandbox_exec", _broker)
    monkeypatch.setattr("agent_tools.sandbox_bridge.run_subprocess_in_sandbox", _local_sandbox)

    with patch(
        "agent_tools.shell_tools.validate_shell_invocation",
        return_value=("pytest", ["-q"]),
    ):
        result = tool_run_shell(tmp_path, "pytest", ["-q"])

    assert result.ok is True
    assert result.tool == "shell"
    assert "broker ok" in result.llm_output
    assert broker_called == [(["pytest", "-q"], str(tmp_path))]
    assert sandbox_called == []


def test_tool_run_shell_falls_back_when_broker_returns_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_SANDBOX", raising=False)
    monkeypatch.delenv("NIMBUSWARE_BROKER_TOOLS", raising=False)
    proc = MagicMock()
    proc.combined_output = "local ok"
    proc.returncode = 0
    proc.backend = "none"

    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.try_broker_sandbox_exec", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        "broker_client.stage_bind.tools.try_broker_shell_exec",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.run_subprocess_in_sandbox",
        lambda *_a, **_k: proc,
    )

    with patch(
        "agent_tools.shell_tools.validate_shell_invocation",
        return_value=("pytest", ["-q"]),
    ):
        result = tool_run_shell(tmp_path, "pytest", ["-q"])

    assert result.ok is True
    assert "local ok" in result.llm_output


def test_tool_run_shell_uses_tools_broker_when_sandbox_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_SANDBOX", raising=False)
    tools_called: list[tuple[list[str], str]] = []

    def _tools(argv: list[str], cwd: str = ".") -> dict:
        tools_called.append((argv, cwd))
        return {"exit_code": 0, "stdout": "tools broker ok"}

    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.try_broker_sandbox_exec", lambda *_a, **_k: None
    )
    monkeypatch.setattr("broker_client.stage_bind.tools.try_broker_shell_exec", _tools)

    with patch(
        "agent_tools.shell_tools.validate_shell_invocation",
        return_value=("pytest", ["-q"]),
    ):
        result = tool_run_shell(tmp_path, "pytest", ["-q"])

    assert result.ok is True
    assert "tools broker ok" in result.llm_output
    assert tools_called == [(["pytest", "-q"], str(tmp_path))]
