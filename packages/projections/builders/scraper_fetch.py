from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from projections.fields.scraper_fetch import SCRAPER_FETCH_ROW_KEYS

_SCRAPER_FETCH_STAGE = "scraper:fetch"


def scraper_fetch_row_sanitized(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    out: dict[str, Any] = {}
    for key in SCRAPER_FETCH_ROW_KEYS:
        if key not in row:
            continue
        val = row[key]
        if key in ("http_status", "bytes", "attempts", "content_length"):
            if isinstance(val, int) and not isinstance(val, bool):
                out[key] = val
        elif key == "artifact_relpath":
            if isinstance(val, str) and val.strip():
                out[key] = val.strip()
        elif key == "url_host":
            if isinstance(val, str) and val.strip():
                out[key] = val.strip()
    return out or None


def scraper_fetch_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest terminal ``scraper:fetch`` stage (``stage.passed`` or ``stage.failed``)."""
    out: dict[str, Any] | None = None
    passed_want = EventType.STAGE_PASSED.value
    failed_want = EventType.STAGE_FAILED.value
    for ev in events:
        et = ev.get("event_type")
        if et not in (passed_want, failed_want):
            continue
        payload = ev.get("payload")
        pl = mapping_or_empty(payload)
        sn = pl.get("stage_name")
        if sn != _SCRAPER_FETCH_STAGE:
            continue
        meta_d = mapping_or_empty(ev.get("metadata"))
        sf_d = mapping_or_empty(meta_d.get("scraper_fetch"))
        fetches = sf_d.get("fetches")
        fetch_list = fetches if isinstance(fetches, list) else []
        fetch_count = 0
        total_bytes = 0
        for row in fetch_list:
            if not isinstance(row, dict):
                continue
            fetch_count += 1
            b = row.get("bytes")
            if isinstance(b, int) and not isinstance(b, bool):
                total_bytes += b
        outcome = "passed" if et == passed_want else "failed"
        out = {
            "event_id": ev.get("event_id"),
            "occurred_at": ev.get("occurred_at"),
            "outcome": outcome,
            "stage_name": sn,
            "fetch_count": fetch_count,
            "total_bytes": total_bytes,
        }
        host = sf_d.get("failed_url_host")
        if isinstance(host, str) and host.strip():
            out["failed_url_host"] = host.strip()
        if outcome == "failed":
            rc = pl.get("reason_code")
            if rc is not None:
                out["reason_code"] = str(rc)
            msg = pl.get("message")
            if msg is not None:
                out["message"] = str(msg)[:500]
        fetch_rows: list[dict[str, Any]] = []
        for row in fetch_list[:25]:
            sanitized = scraper_fetch_row_sanitized(row)
            if sanitized is not None:
                fetch_rows.append(sanitized)
        if fetch_rows:
            out["fetches"] = fetch_rows
    return out


__all__ = [
    "scraper_fetch_row_sanitized",
    "scraper_fetch_timeline_summary",
]
