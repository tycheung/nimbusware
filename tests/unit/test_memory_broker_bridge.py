from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_tools.memory_bridge import try_broker_memory_search
from broker_client import (
    BrokerDisabled,
    bind_compute_work,
    bind_egress_check,
    bind_research_fetch,
    compute_work_via_broker,
    egress_check_via_broker,
    research_fetch_via_broker,
)


def test_bind_research_fetch_returns_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_RESEARCH", "1")
    plan = bind_research_fetch()
    assert plan["offer"] == "research.fetch"
    assert "bind" in plan["steps"]


def test_bind_research_fetch_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_RESEARCH", raising=False)
    with pytest.raises(BrokerDisabled):
        bind_research_fetch()


def test_research_fetch_via_broker_uses_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_RESEARCH", "1")
    mock_mcp = MagicMock()
    mock_mcp.call_tool.return_value = {"body": "html"}

    out = research_fetch_via_broker("https://example.com", client=mock_mcp)

    mock_mcp.call_tool.assert_called_once_with(
        "research_fetch",
        {"url": "https://example.com"},
    )
    assert out == {"body": "html"}


def test_bind_egress_check_returns_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "1")
    plan = bind_egress_check()
    assert plan["offer"] == "network.egress.check"
    assert "bind" in plan["steps"]


def test_egress_check_via_broker_uses_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "1")
    mock_mcp = MagicMock()
    mock_mcp.call_tool.return_value = {"allowed": True}

    out = egress_check_via_broker("https://example.com", client=mock_mcp)

    mock_mcp.call_tool.assert_called_once_with(
        "egress_check",
        {"url": "https://example.com"},
    )
    assert out == {"allowed": True}


def test_bind_compute_work_returns_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    plan = bind_compute_work()
    assert plan["offer"] == "compute.work"
    assert "bind" in plan["steps"]


def test_compute_work_via_broker_uses_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    mock_mcp = MagicMock()
    mock_mcp.call_tool.return_value = {"job_id": "j1"}
    payload = {"kind": "echo", "input": "hi"}

    out = compute_work_via_broker(payload, client=mock_mcp)

    mock_mcp.call_tool.assert_called_once_with(
        "compute_work",
        {"action": "enqueue", "kind": "echo", "payload": payload},
    )
    assert out == {"job_id": "j1"}


def test_try_broker_memory_search_disabled_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_MEMORY", raising=False)
    assert try_broker_memory_search("widget auth") is None


def test_try_broker_memory_search_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")

    import agent_tools.facades.memory_bridge as bridge_mod

    monkeypatch.setattr(
        bridge_mod,
        "memory_search_via_broker",
        lambda query, limit=None, client=None: {"hits": [{"id": "m1"}]},
    )

    out = try_broker_memory_search("widget auth", limit=3)
    assert out == {"hits": [{"id": "m1"}]}


def test_try_broker_memory_search_peel_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak494-d: under MEMORY=1, bridge re-raises (no None soft miss)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")

    import agent_tools.facades.memory_bridge as bridge_mod

    def _boom(*_args, **_kwargs):
        raise RuntimeError("broker down")

    monkeypatch.setattr(bridge_mod, "memory_search_via_broker", _boom)
    with pytest.raises(RuntimeError, match="broker down"):
        try_broker_memory_search("query")


def test_try_broker_memory_search_broker_only_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "2")

    import agent_tools.facades.memory_bridge as bridge_mod

    def _boom(*_args, **_kwargs):
        raise RuntimeError("broker down")

    monkeypatch.setattr(bridge_mod, "memory_search_via_broker", _boom)
    with pytest.raises(RuntimeError, match="broker down"):
        try_broker_memory_search("query")
