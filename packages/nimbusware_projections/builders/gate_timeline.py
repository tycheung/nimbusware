from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nimbusware_projections.builders.timeline_history import timeline_history_tail


def filter_timeline_entries(
    events: list[dict[str, Any]],
    *,
    event_type: str,
    row_from_event: Callable[[dict[str, Any]], dict[str, Any] | None],
) -> list[dict[str, Any]]:
    hist: list[dict[str, Any]] = []
    for ev in events:
        if ev.get("event_type") != event_type:
            continue
        row = row_from_event(ev)
        if row is not None:
            hist.append(row)
    return hist


def timeline_summary(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    return entries[-1] if entries else None


def timeline_history(entries: list[dict[str, Any]], *, limit: int = 25) -> list[dict[str, Any]]:
    return timeline_history_tail(entries, limit=limit)


__all__ = ["filter_timeline_entries", "timeline_history", "timeline_summary"]
