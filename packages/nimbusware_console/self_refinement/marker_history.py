from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from io import StringIO
from typing import Any

from nimbusware_console.self_refinement._helpers import _parse_iso_utc, _stringify


def self_refinement_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("self_refinement")
    return raw if isinstance(raw, dict) else None


def self_refinement_marker_history_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(timeline_body, Mapping):
        return []
    raw = timeline_body.get("self_refinement_marker_history")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def self_refinement_marker_history_table_rows(
    history: list[dict[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i, e in enumerate(history, start=1):
        rows.append(
            {
                "#": str(i),
                "Occurred at": _stringify(e.get("occurred_at")),
                "Version": _stringify(e.get("version")),
                "Event id": _stringify(e.get("event_id")),
            },
        )
    return rows


_SELF_REFINEMENT_MARKER_HISTORY_CSV_COLUMNS: tuple[str, ...] = (
    "#",
    "Occurred at",
    "Version",
    "Event id",
)


def self_refinement_marker_history_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SELF_REFINEMENT_MARKER_HISTORY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _SELF_REFINEMENT_MARKER_HISTORY_CSV_COLUMNS},
            )
    return buf.getvalue()


def self_refinement_marker_history_export_json(
    history: Sequence[Mapping[str, Any]],
) -> str:
    items = [dict(x) for x in history if isinstance(x, Mapping)]
    return json.dumps(items, ensure_ascii=False, indent=2)


def self_refinement_marker_history_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def _marker_history_window_seconds(history: list[dict[str, Any]]) -> int | None:
    stamps: list[datetime] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        parsed = _parse_iso_utc(entry.get("occurred_at"))
        if parsed is not None:
            stamps.append(parsed)
    if len(stamps) < 2:
        return 0 if len(stamps) == 1 else None
    lo, hi = min(stamps), max(stamps)
    delta = hi - lo
    if delta.total_seconds() < 0:
        return None
    return int(delta.total_seconds())


def self_refinement_marker_history_operator_metrics(
    history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "entry_count": 0,
        "distinct_version_count": 0,
        "marker_window_seconds": None,
    }
    if not history:
        return metrics
    versions: set[str] = set()
    for entry in history:
        if not isinstance(entry, dict):
            continue
        metrics["entry_count"] = int(metrics["entry_count"]) + 1
        ver = entry.get("version")
        if ver is not None and str(ver).strip():
            versions.add(str(ver).strip())
    metrics["distinct_version_count"] = len(versions)
    metrics["marker_window_seconds"] = _marker_history_window_seconds(history)
    return metrics


def self_refinement_marker_history_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "Entry count", "value": str(metrics.get("entry_count", 0))},
        {
            "field": "Distinct versions",
            "value": str(metrics.get("distinct_version_count", 0)),
        },
    ]
    window = metrics.get("marker_window_seconds")
    if isinstance(window, int) and not isinstance(window, bool):
        rows.append({"field": "Marker window (s)", "value": str(window)})
    return rows


def self_refinement_marker_history_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    ec = metrics.get("entry_count")
    if isinstance(ec, bool) or not isinstance(ec, int) or ec < 1:
        return None
    parts = [f"**{ec}** marker(s)"]
    dvc = metrics.get("distinct_version_count", 0)
    if isinstance(dvc, int) and not isinstance(dvc, bool) and dvc > 0:
        parts.append(f"**{dvc}** distinct version(s)")
    window = metrics.get("marker_window_seconds")
    if isinstance(window, int) and not isinstance(window, bool) and window > 0:
        parts.append(f"**{window}**s window")
    return "Self-refinement marker history metrics: " + ", ".join(parts) + "."


_SELF_REFINEMENT_MARKER_HISTORY_OPERATOR_METRICS_CSV_COLUMNS: tuple[str, ...] = (
    "field",
    "value",
)


def self_refinement_marker_history_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def self_refinement_marker_history_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SELF_REFINEMENT_MARKER_HISTORY_OPERATOR_METRICS_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {
                    k: r.get(k, "")
                    for k in _SELF_REFINEMENT_MARKER_HISTORY_OPERATOR_METRICS_CSV_COLUMNS
                },
            )
    return buf.getvalue()


def self_refinement_marker_history_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return self_refinement_marker_history_export_filename_slug(run_id, max_len=max_len)


def self_refinement_marker_history_entry_count_caption(
    history: list[dict[str, Any]] | None,
) -> str | None:
    if not history:
        return None
    n = len(history)
    word = "marker" if n == 1 else "markers"
    return f"Self-refinement marker history: **{n}** {word} in this timeline view."

