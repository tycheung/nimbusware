from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_tools.sandbox_bridge import try_broker_sandbox_exec
from broker_client import (
    BrokerDisabled,
    bind_memory_search,
    memory_search_via_broker,
)


def test_bind_memory_search_returns_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    plan = bind_memory_search()
    assert plan["offer"] == "memory.search"
    assert "bind" in plan["steps"]


def test_bind_memory_search_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_MEMORY", raising=False)
    with pytest.raises(BrokerDisabled):
        bind_memory_search()


def test_memory_search_via_broker_uses_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    mock_mcp = MagicMock()
    mock_mcp.call_offer_tool.return_value = {"hits": [{"id": "m1"}]}

    out = memory_search_via_broker("widget auth", client=mock_mcp, limit=5)

    mock_mcp.call_offer_tool.assert_called_once_with(
        "memory_search",
        "memory.search",
        {"query": "widget auth", "k": 5},
    )
    assert out == {"hits": [{"id": "m1"}]}


def test_memory_search_via_broker_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_MEMORY", raising=False)
    with pytest.raises(BrokerDisabled):
        memory_search_via_broker("query")


def test_memory_search_via_broker_raises_on_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak495-g: MCP memory_search peel miss raises via assert_memory_ok."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    mock_mcp = MagicMock()
    mock_mcp.call_offer_tool.return_value = {
        "via": "broker_miss",
        "status": "degraded",
        "feature": "memory_search",
        "error": "down",
        "hits": [],
    }

    with pytest.raises(RuntimeError, match="broker_miss"):
        memory_search_via_broker("widget auth", client=mock_mcp)


def test_assert_memory_ok_empty_vs_miss() -> None:
    """sak495-g: peel_assert memory — empty hits ok; null/miss raises."""
    from broker_client.peel_assert import assert_memory_ok, is_memory_miss

    assert assert_memory_ok({"hits": []}, feature="memory_search")["hits"] == []
    assert is_memory_miss({"code": "broker_memory_only"}) is True
    assert is_memory_miss({"hits": [], "via": "broker"}) is False
    with pytest.raises(RuntimeError, match="missing or non-list key 'hits'"):
        assert_memory_ok({"hits": None}, feature="memory_search")
    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_memory_ok(
            {
                "via": "broker_miss",
                "status": "degraded",
                "feature": "fleet_memory_search",
                "hits": [],
            },
            feature="fleet_memory_search",
        )


def test_try_broker_sandbox_exec_disabled_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_SANDBOX", raising=False)
    assert try_broker_sandbox_exec(["echo", "hi"]) is None


def test_try_broker_sandbox_exec_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_SANDBOX", "1")

    import agent_tools.facades.sandbox_bridge as bridge_mod

    monkeypatch.setattr(
        bridge_mod,
        "sandbox_exec_via_broker",
        lambda argv, cwd=".", client=None: {"exit_code": 0, "stdout": "ok"},
    )

    out = try_broker_sandbox_exec(["echo", "hi"], cwd="/tmp")
    assert out == {"exit_code": 0, "stdout": "ok"}


def test_try_broker_sandbox_exec_peel_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak494-d: under SANDBOX=1, bridge re-raises (no None soft miss)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_SANDBOX", "1")

    import agent_tools.facades.sandbox_bridge as bridge_mod

    def _boom(*_args, **_kwargs):
        raise RuntimeError("broker down")

    monkeypatch.setattr(bridge_mod, "sandbox_exec_via_broker", _boom)
    with pytest.raises(RuntimeError, match="broker down"):
        try_broker_sandbox_exec(["echo"])


def test_try_broker_sandbox_exec_broker_only_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_SANDBOX", "2")

    import agent_tools.facades.sandbox_bridge as bridge_mod

    def _boom(*_args, **_kwargs):
        raise RuntimeError("broker down")

    monkeypatch.setattr(bridge_mod, "sandbox_exec_via_broker", _boom)
    with pytest.raises(RuntimeError, match="broker down"):
        try_broker_sandbox_exec(["echo"])
