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


def pressure_history_from_event_rows(
    rows: list[dict[str, Any]],
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return newest ``hardware.profile.detected`` rows with pressure fields."""
    cap = max(1, min(int(limit), 200))
    hits: list[dict[str, Any]] = []
    for row in reversed(rows):
        if row.get("event_type") != EventType.HARDWARE_PROFILE_DETECTED.value:
            continue
        pl = row.get("payload")
        if not isinstance(pl, dict):
            continue
        level = str(pl.get("pressure_level") or "ok").strip().lower()
        occurred = row.get("occurred_at")
        hits.append(
            {
                "occurred_at": occurred.isoformat() if hasattr(occurred, "isoformat") else occurred,
                "pressure_level": level,
                "pressure_reason": pl.get("pressure_reason"),
                "hardware_tier": pl.get("hardware_tier") or pl.get("tier"),
                "ram_used_pct": _ram_used_pct_from_payload(pl),
                "run_id": str(row["run_id"]) if row.get("run_id") is not None else None,
            },
        )
        if len(hits) >= cap:
            break
    return hits
