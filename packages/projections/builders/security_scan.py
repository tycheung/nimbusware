from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from projections.builders.gate_timeline import (
    filter_timeline_entries,
    timeline_history,
    timeline_summary,
)
from projections.fields.security_scan import SECURITY_SCAN_ROW_KEYS


def _finding_has_security_scan_metadata(meta: Any) -> bool:
    if not isinstance(meta, dict):
        return False
    return "security_scan_exit" in meta or "security_scan_snippet" in meta


def security_scan_row_from_event(ev: dict[str, Any]) -> dict[str, Any] | None:
    meta = ev.get("metadata")
    if not _finding_has_security_scan_metadata(meta):
        return None
    m = mapping_or_empty(meta)
    pl = mapping_or_empty(ev.get("payload"))
    return {
        "event_id": ev.get("event_id"),
        "occurred_at": ev.get("occurred_at"),
        "finding_id": pl.get("finding_id"),
        "category": pl.get("category"),
        "severity": pl.get("severity"),
        "source_artifact": pl.get("source_artifact"),
        "security_scan_exit": m.get("security_scan_exit"),
        "security_scan_ruff_exit": m.get("security_scan_ruff_exit"),
        "security_scan_bandit_exit": m.get("security_scan_bandit_exit"),
        "security_scan_snippet": m.get("security_scan_snippet"),
    }


def security_scan_on_verify_timeline_entries(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return filter_timeline_entries(
        events,
        event_type=EventType.FINDING_CREATED.value,
        row_from_event=security_scan_row_from_event,
    )


def security_scan_on_verify_timeline_summary(
    events: list[dict[str, Any]],
) -> dict[str, Any] | None:
    return timeline_summary(security_scan_on_verify_timeline_entries(events))


def security_scan_on_verify_timeline_history(
    events: list[dict[str, Any]],
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    return timeline_history(security_scan_on_verify_timeline_entries(events), limit=limit)


__all__ = [
    "SECURITY_SCAN_ROW_KEYS",
    "_finding_has_security_scan_metadata",
    "security_scan_on_verify_timeline_entries",
    "security_scan_on_verify_timeline_history",
    "security_scan_on_verify_timeline_summary",
    "security_scan_row_from_event",
]
