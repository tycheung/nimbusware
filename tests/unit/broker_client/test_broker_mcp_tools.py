from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from broker_client import (
    BrokerDisabled,
    BrokerMcpClient,
    bind_llm_chat,
    bind_sandbox_exec,
    llm_chat_via_broker,
    sandbox_exec_via_broker,
)


def test_call_tool_initialize_then_tools_call(mock_post_sequence) -> None:
    mock_client = MagicMock(spec=httpx.Client)
    posts = mock_post_sequence(
        mock_client,
        [
            {"jsonrpc": "2.0", "id": 1, "result": {}},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"content": [{"type": "text", "text": "ok"}]},
            },
        ],
    )
    posts[0].headers = {"mcp-session-id": "sess-1"}

    client = BrokerMcpClient("http://127.0.0.1:8080/mcp", token="tok", client=mock_client)
    out = client.call_tool("ping")

    assert mock_client.post.call_count == 2
    init_call, tool_call = mock_client.post.call_args_list
    assert init_call.kwargs["json"]["method"] == "initialize"
    assert tool_call.kwargs["json"]["method"] == "tools/call"
    assert tool_call.kwargs["json"]["params"] == {"name": "ping", "arguments": {}}
    assert tool_call.kwargs["headers"]["Authorization"] == "Bearer tok"
    assert tool_call.kwargs["headers"]["mcp-session-id"] == "sess-1"
    assert out == {"content": [{"type": "text", "text": "ok"}]}


def test_bind_llm_chat_returns_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    plan = bind_llm_chat()
    assert plan["offer"] == "llm.chat"
    assert "bind" in plan["steps"]


def test_bind_llm_chat_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    with pytest.raises(BrokerDisabled):
        bind_llm_chat()


def test_llm_chat_via_broker_uses_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    mock_mcp = MagicMock()
    mock_mcp.call_tool.return_value = {"text": "hello"}

    out = llm_chat_via_broker([{"role": "user", "content": "hi"}], client=mock_mcp)

    mock_mcp.call_tool.assert_called_once_with(
        "llm_chat",
        {"messages": [{"role": "user", "content": "hi"}]},
    )
    assert out == {"text": "hello"}


def test_llm_chat_via_broker_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    with pytest.raises(BrokerDisabled):
        llm_chat_via_broker([{"role": "user", "content": "hi"}])


def test_bind_sandbox_exec_returns_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_SANDBOX", "1")
    plan = bind_sandbox_exec()
    assert plan["offer"] == "sandbox.exec"
    assert "bind" in plan["steps"]


def test_bind_sandbox_exec_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_SANDBOX", raising=False)
    with pytest.raises(BrokerDisabled):
        bind_sandbox_exec()


def test_sandbox_exec_via_broker_uses_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_SANDBOX", "1")
    mock_mcp = MagicMock()
    mock_mcp.call_tool.return_value = {"exit_code": 0, "stdout": "ok"}

    out = sandbox_exec_via_broker(["echo", "hi"], cwd="/tmp", client=mock_mcp)

    mock_mcp.call_tool.assert_called_once_with(
        "sandbox_exec",
        {"argv": ["echo", "hi"], "cwd": "/tmp"},
    )
    assert out == {"exit_code": 0, "stdout": "ok"}


def test_sandbox_exec_via_broker_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_SANDBOX", raising=False)
    with pytest.raises(BrokerDisabled):
        sandbox_exec_via_broker(["echo"])


def test_sandbox_exec_via_broker_raises_on_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-g: MCP sandbox_exec peel miss raises via assert_sandbox_ok."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_SANDBOX", "1")
    mock_mcp = MagicMock()
    mock_mcp.call_tool.return_value = {
        "via": "broker_miss",
        "status": "degraded",
        "feature": "sandbox_exec",
        "error": "down",
    }

    with pytest.raises(RuntimeError, match="broker_miss"):
        sandbox_exec_via_broker(["echo"], client=mock_mcp)


def test_llm_chat_via_broker_raises_on_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-g: MCP llm_chat peel miss raises via assert_llm_ok."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    mock_mcp = MagicMock()
    mock_mcp.call_tool.return_value = {
        "via": "broker_miss",
        "status": "degraded",
        "feature": "llm_chat",
        "error": "down",
    }

    with pytest.raises(RuntimeError, match="broker_miss"):
        llm_chat_via_broker([{"role": "user", "content": "hi"}], client=mock_mcp)


def test_broker_client_domain_helpers_use_assert(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-g: BrokerClient domain MCP helpers raise on peel miss."""
    from broker_client.client import BrokerClient

    mock_mcp = MagicMock()
    mock_mcp.call_tool.return_value = {
        "via": "broker_miss",
        "error": "down",
        "feature": "sandbox_exec",
    }
    client = BrokerClient("http://127.0.0.1:8787")

    with pytest.raises(RuntimeError, match="broker_miss"):
        client.sandbox_exec(["echo"], mcp=mock_mcp)

    mock_mcp.call_tool.return_value = {"stdout": "ok", "via": "broker"}
    assert client.sandbox_exec(["echo"], mcp=mock_mcp)["stdout"] == "ok"
