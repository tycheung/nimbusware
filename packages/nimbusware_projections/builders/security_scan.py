from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from nimbusware_projections.builders.timeline_history import timeline_history_tail
from nimbusware_projections.fields.security_scan import SECURITY_SCAN_ROW_KEYS


def _finding_has_security_scan_metadata(meta: Any) -> bool:
    if not isinstance(meta, dict):
        return False
    return "security_scan_exit" in meta or "security_scan_snippet" in meta


def security_scan_row_from_event(ev: dict[str, Any]) -> dict[str, Any] | None:
    """Shape one security-scan finding row (caller filters event type)."""
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
    """Chronological security-scan ``finding.created`` rows (``store_seq`` order)."""
    want = EventType.FINDING_CREATED.value
    hist: list[dict[str, Any]] = []
    for ev in events:
        if ev.get("event_type") != want:
            continue
        row = security_scan_row_from_event(ev)
        if row is not None:
            hist.append(row)
    return hist


def security_scan_on_verify_timeline_summary(
    events: list[dict[str, Any]],
) -> dict[str, Any] | None:
    hist = security_scan_on_verify_timeline_entries(events)
    return hist[-1] if hist else None


def security_scan_on_verify_timeline_history(
    events: list[dict[str, Any]],
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Bounded security-scan history for operator drill-down."""
    hist = security_scan_on_verify_timeline_entries(events)
    return timeline_history_tail(hist, limit=limit)


__all__ = [
    "SECURITY_SCAN_ROW_KEYS",
    "_finding_has_security_scan_metadata",
    "security_scan_on_verify_timeline_entries",
    "security_scan_on_verify_timeline_history",
    "security_scan_on_verify_timeline_summary",
    "security_scan_row_from_event",
]
