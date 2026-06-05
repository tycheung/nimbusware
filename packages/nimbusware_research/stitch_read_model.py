from __future__ import annotations

from typing import Any

from agent_core.models import EventType


def has_code_research_brief(events: list[dict[str, Any]]) -> bool:
    for row in events:
        if row.get("event_type") != EventType.RESEARCH_BRIEF_EMITTED.value:
            continue
        payload = row.get("payload")
        if isinstance(payload, dict) and payload.get("brief_kind") == "code":
            return True
    return False


def stitch_applied_snapshot_from_events(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    for row in events:
        if row.get("event_type") != EventType.STITCH_APPLIED.value:
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        snap = meta.get("workspace_snapshot")
        if isinstance(snap, dict) and snap.get("snapshot_id"):
            latest = dict(snap)
    return latest


def stitch_events_present(events: list[dict[str, Any]]) -> bool:
    stitch_types = {
        EventType.STITCH_APPLIED.value,
        EventType.STITCH_FAILED.value,
    }
    return any(str(row.get("event_type") or "") in stitch_types for row in events)
