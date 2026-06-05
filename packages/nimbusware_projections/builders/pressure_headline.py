from __future__ import annotations

from typing import Any

_PRESSURE_MESSAGES = {
    "warn": "Memory use is near the governor cap — some parallel work may slow down.",
    "throttle": "Governor is throttling parallel writers due to memory pressure.",
    "block": "Memory pressure is blocking extra parallel work until RAM recovers.",
}


def pressure_headline(level: str, payload: dict[str, Any] | None = None) -> str:
    pl = payload if isinstance(payload, dict) else {}
    base = _PRESSURE_MESSAGES.get(level, f"Resource pressure: {level}")
    reason = pl.get("pressure_reason")
    if isinstance(reason, str) and reason.strip():
        return f"{base} ({reason.strip()})"
    return base


def latest_resource_pressure_from_events(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    from agent_core.models import EventType

    latest: dict[str, Any] | None = None
    for row in events:
        et = row.get("event_type")
        if et not in (
            EventType.HARDWARE_PROFILE_DETECTED.value,
            EventType.RESOURCE_PRESSURE_WARN.value,
        ):
            continue
        pl = row.get("payload")
        if not isinstance(pl, dict):
            continue
        level = str(pl.get("pressure_level") or "").strip().lower()
        if not level or level == "ok":
            continue
        latest = {
            "level": level,
            "reason": pl.get("pressure_reason"),
            "hardware_tier": pl.get("hardware_tier") or pl.get("tier"),
            "headline": pressure_headline(level, pl),
        }
    return latest
