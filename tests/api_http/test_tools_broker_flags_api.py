from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from agent_tools.broker_route import map_broker_tools_http_miss
from agent_tools.shell_tools import tool_run_shell


def test_map_tools_miss_under_tools_1(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak497-i: map_broker_tools_http_miss returns broker_miss under TOOLS=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOOLS", "1")
    out = map_broker_tools_http_miss(
        RuntimeError("broker_miss: shell: down"),
        feature="shell",
    )
    assert out.get("via") == "broker_miss"
    assert out.get("feature") == "shell"
    assert out.get("status") == "degraded"


def test_map_tools_miss_under_tools_2_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak497-i: map_broker_tools_http_miss maps to 503 under TOOLS=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOOLS", "2")
    with pytest.raises(HTTPException) as ei:
        map_broker_tools_http_miss(
            RuntimeError("broker_miss: shell: down"),
            feature="shell",
        )
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_tools_only"


def test_tool_run_shell_under_tools_1_broker_miss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak497-i: tool_run_shell raises broker_miss under TOOLS=1 when broker returns None."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_SANDBOX", raising=False)
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOOLS", "1")
    local_called: list[object] = []
    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.try_broker_sandbox_exec",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "broker_client.stage_bind.tools.try_broker_shell_exec",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.run_subprocess_in_sandbox",
        lambda *_a, **_k: local_called.append(True),
    )
    with patch(
        "agent_tools.shell_tools.validate_shell_invocation",
        return_value=("pytest", ["-q"]),
    ):
        with pytest.raises(RuntimeError, match="broker_miss: shell"):
            tool_run_shell(tmp_path, "pytest", ["-q"])
    assert local_called == []


def test_tool_run_shell_under_tools_1_broker_hit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak497-i: tool_run_shell returns broker result under TOOLS=1 on shell hit."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_SANDBOX", raising=False)
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOOLS", "1")
    monkeypatch.setattr(
        "agent_tools.sandbox_bridge.try_broker_sandbox_exec",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        "broker_client.stage_bind.tools.try_broker_shell_exec",
        lambda *_a, **_k: {"exit_code": 0, "stdout": "tools-ok"},
    )
    with patch(
        "agent_tools.shell_tools.validate_shell_invocation",
        return_value=("echo", ["tools-ok"]),
    ):
        out = tool_run_shell(tmp_path, "echo", ["tools-ok"])
    assert out.ok is True
    assert "tools-ok" in out.output
