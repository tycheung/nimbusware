from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from broker_client import (
    BrokerDisabled,
    bind_tools_shell,
    shell_exec_via_broker,
    try_broker_shell_exec,
)
from research.research_bridge import try_broker_research_fetch


def test_bind_tools_shell_returns_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOOLS", "1")
    plan = bind_tools_shell()
    assert plan["offer"] == "tools.shell"
    assert "bind" in plan["steps"]


def test_bind_tools_shell_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_TOOLS", raising=False)
    with pytest.raises(BrokerDisabled):
        bind_tools_shell()


def test_shell_exec_via_broker_uses_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOOLS", "1")
    mock_mcp = MagicMock()
    mock_mcp.call_tool.return_value = {"exit_code": 0, "stdout": "ok"}

    out = shell_exec_via_broker(["echo", "hi"], cwd="/tmp", client=mock_mcp)

    mock_mcp.call_tool.assert_called_once_with(
        "shell_exec",
        {"argv": ["echo", "hi"], "cwd": "/tmp"},
    )
    assert out == {"exit_code": 0, "stdout": "ok"}


def test_shell_exec_via_broker_raises_on_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-g: MCP shell_exec peel miss raises via assert_tools_ok."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOOLS", "1")
    mock_mcp = MagicMock()
    mock_mcp.call_tool.return_value = {
        "via": "broker_miss",
        "status": "degraded",
        "feature": "shell_exec",
        "error": "down",
    }

    with pytest.raises(RuntimeError, match="broker_miss"):
        shell_exec_via_broker(["echo", "hi"], client=mock_mcp)


def test_try_broker_shell_exec_disabled_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_TOOLS", raising=False)
    assert try_broker_shell_exec(["echo"]) is None


def test_try_broker_shell_exec_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOOLS", "1")

    import broker_client.stage_bind.tools as tools_mod

    monkeypatch.setattr(
        tools_mod,
        "shell_exec_via_broker",
        lambda argv, cwd=".", client=None: {"exit_code": 0, "stdout": "ok"},
    )

    out = try_broker_shell_exec(["echo", "hi"], cwd="/tmp")
    assert out == {"exit_code": 0, "stdout": "ok"}


def test_try_broker_shell_exec_swallows_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOOLS", "1")

    import broker_client.stage_bind.tools as tools_mod

    def _boom(*_args, **_kwargs):
        raise RuntimeError("broker down")

    monkeypatch.setattr(tools_mod, "shell_exec_via_broker", _boom)
    assert try_broker_shell_exec(["echo"]) is None


def test_try_broker_shell_exec_broker_only_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak495-i: under TOOLS=2, bridge re-raises (no None soft miss)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOOLS", "2")

    import broker_client.stage_bind.tools as tools_mod

    def _boom(*_args, **_kwargs):
        raise RuntimeError("broker down")

    monkeypatch.setattr(tools_mod, "shell_exec_via_broker", _boom)
    with pytest.raises(RuntimeError, match="broker down"):
        try_broker_shell_exec(["echo"])


def test_try_broker_research_fetch_disabled_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_RESEARCH", raising=False)
    assert try_broker_research_fetch("https://example.com") is None


def test_try_broker_research_fetch_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_RESEARCH", "1")

    import research.research_bridge as bridge_mod

    monkeypatch.setattr(
        bridge_mod,
        "research_fetch_via_broker",
        lambda url, **kwargs: {"body": "html"},
    )

    out = try_broker_research_fetch("https://example.com")
    assert out == {"body": "html"}


def test_try_broker_research_fetch_swallows_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_RESEARCH", "1")

    import research.research_bridge as bridge_mod

    def _boom(*_args, **_kwargs):
        raise RuntimeError("broker down")

    monkeypatch.setattr(bridge_mod, "research_fetch_via_broker", _boom)
    assert try_broker_research_fetch("https://example.com") is None


def test_try_broker_research_fetch_broker_only_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_RESEARCH", "2")

    import research.research_bridge as bridge_mod

    def _boom(*_args, **_kwargs):
        raise RuntimeError("broker down")

    monkeypatch.setattr(bridge_mod, "research_fetch_via_broker", _boom)
    with pytest.raises(RuntimeError, match="broker down"):
        try_broker_research_fetch("https://example.com")
