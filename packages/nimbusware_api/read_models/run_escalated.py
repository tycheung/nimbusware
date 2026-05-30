from __future__ import annotations

from typing import Any

from agent_core.models import EventType


def _run_escalated_row_from_event(ev: dict[str, Any]) -> dict[str, Any]:
    """Shape one timeline row from a ``run.escalated`` event."""
    payload = ev.get("payload")
    pl: dict[str, Any] = payload if isinstance(payload, dict) else {}
    return {
        "event_id": ev.get("event_id"),
        "occurred_at": ev.get("occurred_at"),
        "actor_id": pl.get("actor_id"),
        "reason_code": pl.get("reason_code"),
        "policy_snapshot_id": pl.get("policy_snapshot_id"),
        "notes": pl.get("notes"),
    }


def run_escalated_timeline_entries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chronological ``run.escalated`` events (``store_seq`` order of ``events``)."""
    want = EventType.RUN_ESCALATED.value
    hist: list[dict[str, Any]] = []
    for ev in events:
        if ev.get("event_type") != want:
            continue
        hist.append(_run_escalated_row_from_event(ev))
    return hist


def run_escalated_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest ``run.escalated`` event summary (human / system escalation checkpoint)."""
    hist = run_escalated_timeline_entries(events)
    return hist[-1] if hist else None


def run_escalated_timeline_history(
    events: list[dict[str, Any]],
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Bounded run escalation history for operator drill-down."""
    hist = run_escalated_timeline_entries(events)
    if not hist:
        return []
    if len(hist) <= limit:
        return hist
    return hist[-limit:]


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


