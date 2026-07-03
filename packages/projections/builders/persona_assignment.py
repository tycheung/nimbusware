from __future__ import annotations

from typing import Any

from agent_core.models import EventType
from agent_core.timeline_metadata import persona_assignment_from_run_created_metadata


def persona_assignment_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Frozen composite persona from first ``run.created`` (same as run summary)."""
    want = EventType.RUN_CREATED.value
    for ev in events:
        if ev.get("event_type") != want:
            continue
        meta = ev.get("metadata")
        if not isinstance(meta, dict):
            return None
        return persona_assignment_from_run_created_metadata(meta)
    return None


__all__ = ["persona_assignment_timeline_summary"]
