from __future__ import annotations

import pytest

from agent_tools.memory_bridge import try_broker_memory_search
from agent_tools.shell_tools import tool_memory_search
from broker_client import BrokerDisabled, bind_memory_search, broker_memory_enabled, select_backend


def test_sak405_e_memory_dual_run_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_MEMORY", raising=False)

    assert broker_memory_enabled() is False
    assert select_backend("memory") == "python"
    assert try_broker_memory_search("widget auth") is None

    with pytest.raises(BrokerDisabled):
        bind_memory_search()

    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")

    assert broker_memory_enabled() is True
    assert select_backend("memory") == "broker"


def test_sak405_e_tool_memory_search_broker_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "agent_tools.memory_bridge.try_broker_memory_search",
        lambda query, limit=None: {
            "hits": [{"chunk_id": "c1", "score": 0.9, "excerpt": "widget auth flow"}],
        },
    )
    result = tool_memory_search("widget auth")
    assert result.ok is True
    assert result.tool == "memory_search"
    assert "widget auth flow" in result.llm_output
    assert "broker hits=1" in result.audit_output
