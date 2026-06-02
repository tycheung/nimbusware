from __future__ import annotations

import csv
import json
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from nimbusware_console.run_list_pagination_display.run_detail_summary import (
    run_detail_summary_export_filename_slug,
)


def timeline_events_from_body(body: Mapping[str, Any] | None) -> list[Any]:
    if not isinstance(body, Mapping):
        return []
    raw = body.get("events")
    if not isinstance(raw, list):
        return []
    return raw


def _timeline_event_stringify(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def timeline_events_table_rows(events: Sequence[Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        rows.append(
            {
                "event_type": _timeline_event_stringify(ev.get("event_type")),
                "occurred_at": _timeline_event_stringify(ev.get("occurred_at")),
                "event_id": _timeline_event_stringify(ev.get("event_id")),
            },
        )
    return rows


_TIMELINE_EVENTS_CSV_COLUMNS: tuple[str, ...] = ("event_type", "occurred_at", "event_id")


def timeline_events_table_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_TIMELINE_EVENTS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _TIMELINE_EVENTS_CSV_COLUMNS})
    return buf.getvalue()


def timeline_events_export_json(body: Mapping[str, Any] | None) -> str:
    events = timeline_events_from_body(body)
    return json.dumps(events, indent=2, ensure_ascii=False)


def timeline_events_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    return run_detail_summary_export_filename_slug(run_id, max_len=max_len)


def timeline_events_operator_metrics(
    events: Sequence[Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "event_count": 0,
        "distinct_event_type_count": 0,
        "top_event_type": None,
        "top_event_type_count": 0,
    }
    if not events:
        return metrics
    type_counts: dict[str, int] = {}
    for ev in events:
        if not isinstance(ev, dict):
            continue
        metrics["event_count"] = int(metrics["event_count"]) + 1
        et = ev.get("event_type")
        if isinstance(et, str) and et.strip():
            key = et.strip()
            type_counts[key] = type_counts.get(key, 0) + 1
    metrics["distinct_event_type_count"] = len(type_counts)
    if type_counts:
        top_type, top_count = max(type_counts.items(), key=lambda x: (x[1], x[0]))
        metrics["top_event_type"] = top_type
        metrics["top_event_type_count"] = top_count
    return metrics


def timeline_events_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "Event count", "value": str(metrics.get("event_count", 0))},
        {
            "field": "Distinct event types",
            "value": str(metrics.get("distinct_event_type_count", 0)),
        },
    ]
    top = metrics.get("top_event_type")
    tc = metrics.get("top_event_type_count", 0)
    if isinstance(top, str) and top.strip() and isinstance(tc, int) and not isinstance(tc, bool):
        rows.append({"field": "Top event type", "value": f"{top.strip()} ({tc})"})
    return rows


def timeline_events_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    ec = metrics.get("event_count")
    if isinstance(ec, bool) or not isinstance(ec, int) or ec < 1:
        return None
    parts = [f"**{ec}** event(s)"]
    det = metrics.get("distinct_event_type_count", 0)
    if isinstance(det, int) and not isinstance(det, bool) and det > 0:
        parts.append(f"**{det}** distinct type(s)")
    top = metrics.get("top_event_type")
    if isinstance(top, str) and top.strip():
        parts.append(f"top type `{top.strip()}`")
    return "Timeline events metrics: " + ", ".join(parts) + "."


_TIMELINE_EVENTS_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def timeline_events_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def timeline_events_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_TIMELINE_EVENTS_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _TIMELINE_EVENTS_OPERATOR_METRICS_CSV_COLUMNS},
            )
    return buf.getvalue()


def timeline_events_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return timeline_events_export_filename_slug(run_id, max_len=max_len)
