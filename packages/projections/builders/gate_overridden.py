from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from projections.builders.gate_timeline import (
    filter_timeline_entries,
    timeline_history,
    timeline_summary,
)


def gate_overridden_row_from_event(ev: dict[str, Any]) -> dict[str, Any]:
    payload = ev.get("payload")
    pl = mapping_or_empty(payload)
    return {
        "event_id": ev.get("event_id"),
        "occurred_at": ev.get("occurred_at"),
        "actor_id": pl.get("actor_id"),
        "reason_code": pl.get("reason_code"),
        "stage_name": pl.get("stage_name"),
        "policy_snapshot_id": pl.get("policy_snapshot_id"),
    }


def gate_overridden_timeline_entries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return filter_timeline_entries(
        events,
        event_type=EventType.GATE_OVERRIDDEN.value,
        row_from_event=gate_overridden_row_from_event,
    )


def gate_overridden_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    return timeline_summary(gate_overridden_timeline_entries(events))


def gate_overridden_timeline_history(
    events: list[dict[str, Any]],
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    return timeline_history(gate_overridden_timeline_entries(events), limit=limit)


__all__ = [
    "gate_overridden_row_from_event",
    "gate_overridden_timeline_entries",
    "gate_overridden_timeline_history",
    "gate_overridden_timeline_summary",
]
