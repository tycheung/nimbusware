from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from projections.builders.gate_timeline import (
    filter_timeline_entries,
    timeline_history,
    timeline_summary,
)


def run_escalated_row_from_event(ev: dict[str, Any]) -> dict[str, Any]:
    """Shape one timeline row from a ``run.escalated`` event."""
    payload = ev.get("payload")
    pl = mapping_or_empty(payload)
    return {
        "event_id": ev.get("event_id"),
        "occurred_at": ev.get("occurred_at"),
        "actor_id": pl.get("actor_id"),
        "reason_code": pl.get("reason_code"),
        "policy_snapshot_id": pl.get("policy_snapshot_id"),
        "notes": pl.get("notes"),
    }


def run_escalated_timeline_entries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return filter_timeline_entries(
        events,
        event_type=EventType.RUN_ESCALATED.value,
        row_from_event=run_escalated_row_from_event,
    )


def run_escalated_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    return timeline_summary(run_escalated_timeline_entries(events))


def run_escalated_timeline_history(
    events: list[dict[str, Any]],
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    return timeline_history(run_escalated_timeline_entries(events), limit=limit)


def run_escalated_timeline_delta(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest escalation vs the immediately prior (needs at least two events)."""
    hist = run_escalated_timeline_entries(events)
    if len(hist) < 2:
        return None
    prev, cur = hist[-2], hist[-1]
    return {
        "previous_event_id": prev.get("event_id"),
        "current_event_id": cur.get("event_id"),
        "reason_code_changed": prev.get("reason_code") != cur.get("reason_code"),
        "actor_id_changed": prev.get("actor_id") != cur.get("actor_id"),
        "policy_snapshot_id_changed": prev.get("policy_snapshot_id")
        != cur.get("policy_snapshot_id"),
        "previous_reason_code": prev.get("reason_code"),
        "current_reason_code": cur.get("reason_code"),
        "previous_actor_id": prev.get("actor_id"),
        "current_actor_id": cur.get("actor_id"),
    }


__all__ = [
    "run_escalated_row_from_event",
    "run_escalated_timeline_delta",
    "run_escalated_timeline_entries",
    "run_escalated_timeline_history",
    "run_escalated_timeline_summary",
]
