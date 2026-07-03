from __future__ import annotations

import pytest

from agent_core.models import EventType
from projections.builders.agent_tool_prune import (
    projection_prune_agent_tools_enabled,
    prune_agent_tool_log_text,
    prune_all_agent_tool_lines,
    prune_theater_agent_tool_messages,
)


def test_prune_agent_tool_log_keeps_latest_turn_batch() -> None:
    text = "read: old content\nagent: done turn\nread: fresh content\n"
    pruned = prune_agent_tool_log_text(text)
    assert "[pruned: 11 chars]" in pruned
    assert "fresh content" in pruned
    assert "old content" not in pruned


def test_prune_all_agent_tool_lines() -> None:
    text = "read: abc\ngrep: def\n"
    pruned = prune_all_agent_tool_lines(text)
    assert pruned == "read: [pruned: 3 chars]\ngrep: [pruned: 3 chars]"


def test_theater_prune_keeps_latest_batch() -> None:
    messages = [
        {
            "store_seq": 1,
            "message_kind": "agent_tool",
            "body_md": "read: stale output here",
        },
        {
            "store_seq": 5,
            "message_kind": "agent_tool",
            "body_md": "read: keep this line",
        },
        {"store_seq": 2, "message_kind": "slice", "body_md": "ok"},
    ]
    pruned = prune_theater_agent_tool_messages(messages)
    old = pruned[0]["body_md"]
    new = pruned[1]["body_md"]
    assert "[pruned:" in old
    assert "keep this line" in new


def test_projection_prune_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_PROJECTION_PRUNE_AGENT_TOOLS", "0")
    assert projection_prune_agent_tools_enabled() is False


def test_timeline_summary_respects_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from projections.builders.stage_timeline import agent_tool_timeline_summary

    events = [
        {
            "event_type": EventType.STAGE_PASSED.value,
            "store_seq": 3,
            "payload": {"stage_name": "slice.implement"},
            "metadata": {
                "slice_id": "s1",
                "agent_tool_log": "read: secret\nagent: ok\nread: visible\n",
            },
        },
    ]
    monkeypatch.setenv("NIMBUSWARE_PROJECTION_PRUNE_AGENT_TOOLS", "0")
    raw = agent_tool_timeline_summary(events)
    assert raw is not None
    assert "secret" in raw[0]["log"]

    monkeypatch.setenv("NIMBUSWARE_PROJECTION_PRUNE_AGENT_TOOLS", "1")
    pruned = agent_tool_timeline_summary(events)
    assert pruned is not None
    assert "secret" not in pruned[0]["log"]
    assert "visible" in pruned[0]["log"]
