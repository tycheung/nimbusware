from __future__ import annotations

import pytest

from agent_tools.shell_tools import tool_memory_search


def test_tool_memory_search_broker_hits(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_tool_memory_search_local_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Local peel store removed (sak413); without MEMORY peel, broker miss → unavailable."""
    monkeypatch.delenv("NIMBUSWARE_BROKER_MEMORY", raising=False)
    monkeypatch.setattr(
        "agent_tools.memory_bridge.try_broker_memory_search",
        lambda *_a, **_k: None,
    )
    result = tool_memory_search("query", memory_store=object())
    assert result.ok is False
    assert result.llm_output == "memory search unavailable"


def test_tool_memory_search_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_MEMORY", raising=False)
    monkeypatch.setattr(
        "agent_tools.memory_bridge.try_broker_memory_search",
        lambda *_a, **_k: None,
    )
    result = tool_memory_search("query")
    assert result.ok is False
    assert result.llm_output == "memory search unavailable"


def test_tool_memory_search_empty_query() -> None:
    result = tool_memory_search("   ")
    assert result.ok is False
    assert result.llm_output == "empty query"
