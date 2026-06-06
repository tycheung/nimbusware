"""Campaign budgets, rate limits, and pressure deferral."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agent_core.models import EventType


def campaign_started_at(rows: list[dict[str, Any]]) -> datetime | None:
    for row in rows:
        if row.get("event_type") == EventType.CAMPAIGN_CREATED.value:
            raw = row.get("occurred_at")
            if isinstance(raw, datetime):
                return raw
            if isinstance(raw, str):
                try:
                    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    return None
    return None


def campaign_exceeded_duration(rows: list[dict[str, Any]], *, max_hours: int) -> bool:
    started = campaign_started_at(rows)
    if started is None:
        return False
    now = datetime.now(timezone.utc)
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed_hours = (now - started).total_seconds() / 3600.0
    return elapsed_hours > float(max_hours)


def should_defer_tick_for_pressure(rows: list[dict[str, Any]]) -> bool:
    from nimbusware_projections.builders.pressure_headline import (
        latest_resource_pressure_from_events,
    )

    pressure = latest_resource_pressure_from_events(rows)
    if not pressure:
        return False
    return str(pressure.get("level") or "") in {"throttle", "block"}


def active_campaigns_for_project(store: Any, project_id: str) -> int:
    count = 0
    if not hasattr(store, "list_runs"):
        return 0
    try:
        runs = store.list_runs(limit=200)
    except (AttributeError, TypeError, ValueError):
        return 0
    for run in runs or []:
        rid = str(run.get("run_id") or run.get("id") or "")
        if not rid:
            continue
        rows = store.list_run_events(rid)
        for row in rows:
            if row.get("event_type") != EventType.RUN_CREATED.value:
                continue
            meta = row.get("metadata") or {}
            proj = meta.get("project") or {}
            if str(proj.get("project_id") or "") != project_id:
                break
            ce = meta.get("campaign_effective") or {}
            if not ce.get("enabled"):
                break
            terminal = any(
                r.get("event_type")
                in (
                    EventType.CAMPAIGN_COMPLETED.value,
                    EventType.CAMPAIGN_FAILED.value,
                )
                for r in rows
            )
            if not terminal:
                count += 1
            break
    return count
