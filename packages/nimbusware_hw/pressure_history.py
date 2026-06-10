from __future__ import annotations

from typing import Any

from agent_core.models import EventType


def _ram_used_pct_from_payload(pl: dict[str, Any]) -> float | None:
    total = pl.get("ram_total_gb")
    avail = pl.get("ram_available_gb")
    if total is None or avail is None:
        return None
    try:
        total_f = float(total)
        avail_f = float(avail)
    except (TypeError, ValueError):
        return None
    if total_f <= 0:
        return None
    return round((total_f - avail_f) / total_f * 100.0, 1)


def _pressure_row_from_event(row: dict[str, Any]) -> dict[str, Any] | None:
    et = row.get("event_type")
    if et not in (
        EventType.HARDWARE_PROFILE_DETECTED.value,
        EventType.RESOURCE_PRESSURE_WARN.value,
    ):
        return None
    pl = row.get("payload")
    if not isinstance(pl, dict):
        return None
    level = str(pl.get("pressure_level") or "ok").strip().lower()
    occurred = row.get("occurred_at")
    ram_pct = pl.get("ram_used_pct")
    if ram_pct is None:
        ram_pct = _ram_used_pct_from_payload(pl)
    occurred_at: str | Any = occurred
    if occurred is not None and hasattr(occurred, "isoformat"):
        occurred_at = occurred.isoformat()
    return {
        "occurred_at": occurred_at,
        "pressure_level": level,
        "pressure_reason": pl.get("pressure_reason"),
        "hardware_tier": pl.get("hardware_tier") or pl.get("tier"),
        "ram_used_pct": ram_pct,
        "run_id": str(row["run_id"]) if row.get("run_id") is not None else None,
        "event_type": et,
    }


def pressure_history_from_event_rows(
    rows: list[dict[str, Any]],
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return newest hardware profile and mid-run pressure warn rows."""
    cap = max(1, min(int(limit), 200))
    hits: list[dict[str, Any]] = []
    for row in reversed(rows):
        entry = _pressure_row_from_event(row)
        if entry is None:
            continue
        hits.append(entry)
        if len(hits) >= cap:
            break
    return hits
