from __future__ import annotations

from typing import Any

from agent_core.models import EventType


def gate_overridden_row_from_event(ev: dict[str, Any]) -> dict[str, Any]:
    payload = ev.get("payload")
    pl: dict[str, Any] = payload if isinstance(payload, dict) else {}
    return {
        "event_id": ev.get("event_id"),
        "occurred_at": ev.get("occurred_at"),
        "actor_id": pl.get("actor_id"),
        "reason_code": pl.get("reason_code"),
        "stage_name": pl.get("stage_name"),
        "policy_snapshot_id": pl.get("policy_snapshot_id"),
    }


def gate_overridden_timeline_entries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    want = EventType.GATE_OVERRIDDEN.value
    return [gate_overridden_row_from_event(ev) for ev in events if ev.get("event_type") == want]


def gate_overridden_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    hist = gate_overridden_timeline_entries(events)
    return hist[-1] if hist else None


def gate_overridden_timeline_history(
    events: list[dict[str, Any]],
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    hist = gate_overridden_timeline_entries(events)
    if not hist:
        return []
    if len(hist) <= limit:
        return hist
    return hist[-limit:]


__all__ = [
    "gate_overridden_row_from_event",
    "gate_overridden_timeline_entries",
    "gate_overridden_timeline_history",
    "gate_overridden_timeline_summary",
]
