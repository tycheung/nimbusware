from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any

from nimbusware_console.run_escalated._common import _stringify
from nimbusware_projections.fields.run_escalated import RUN_ESCALATED_DISPLAY_FIELDS

def run_escalated_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("run_escalated")
    return raw if isinstance(raw, dict) else None




def run_escalated_summary_rows(summary: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not summary:
        return []
    rows: list[dict[str, str]] = []
    for key, label in RUN_ESCALATED_DISPLAY_FIELDS:
        if key not in summary:
            continue
        rows.append({"field": label, "value": _stringify(summary.get(key))})
    return rows


_RUN_ESCALATED_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")




def run_escalated_summary_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_RUN_ESCALATED_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _RUN_ESCALATED_SUMMARY_CSV_COLUMNS})
    return buf.getvalue()




def run_escalated_export_json(summary: Mapping[str, Any] | None) -> str:
    if not isinstance(summary, Mapping):
        return "{}"
    return json.dumps(dict(summary), ensure_ascii=False, indent=2)




def run_escalated_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]




def run_escalated_history_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    if not isinstance(timeline_body, Mapping):
        return []
    raw = timeline_body.get("run_escalated_history")
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]




def run_escalated_history_table_rows(
    history: list[dict[str, Any]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i, e in enumerate(history, start=1):
        rows.append(
            {
                "#": str(i),
                "Occurred at": _stringify(e.get("occurred_at")),
                "Actor": _stringify(e.get("actor_id")),
                "Reason": _stringify(e.get("reason_code")),
                "Policy snapshot": _stringify(e.get("policy_snapshot_id")),
                "Notes": _stringify(e.get("notes")),
                "Event id": _stringify(e.get("event_id")),
            },
        )
    return rows


_RUN_ESCALATED_HISTORY_CSV_COLUMNS: tuple[str, ...] = (
    "#",
    "Occurred at",
    "Actor",
    "Reason",
    "Policy snapshot",
    "Notes",
    "Event id",
)




def run_escalated_history_table_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_RUN_ESCALATED_HISTORY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _RUN_ESCALATED_HISTORY_CSV_COLUMNS})
    return buf.getvalue()




def run_escalated_history_export_json(history: Sequence[Mapping[str, Any]]) -> str:
    items = [dict(x) for x in history if isinstance(x, Mapping)]
    return json.dumps(items, ensure_ascii=False, indent=2)




def run_escalated_history_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]




def run_escalated_delta_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("run_escalated_delta")
    return raw if isinstance(raw, dict) else None


# Order matches ``run_escalated_timeline_delta`` in runs (latest vs prior escalation).
_RUN_ESCALATED_DELTA_FIELDS: tuple[tuple[str, str], ...] = (
    ("previous_event_id", "Previous event id"),
    ("current_event_id", "Current event id"),
    ("reason_code_changed", "Reason code changed"),
    ("actor_id_changed", "Actor id changed"),
    ("policy_snapshot_id_changed", "Policy snapshot id changed"),
    ("previous_reason_code", "Previous reason code"),
    ("current_reason_code", "Current reason code"),
    ("previous_actor_id", "Previous actor id"),
    ("current_actor_id", "Current actor id"),
)




def run_escalated_delta_summary_rows(delta: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not isinstance(delta, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key, label in _RUN_ESCALATED_DELTA_FIELDS:
        if key not in delta:
            continue
        rows.append({"field": label, "value": _stringify(delta.get(key))})
    return rows


_RUN_ESCALATED_DELTA_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")




def run_escalated_delta_table_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_RUN_ESCALATED_DELTA_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow({k: r.get(k, "") for k in _RUN_ESCALATED_DELTA_SUMMARY_CSV_COLUMNS})
    return buf.getvalue()




def run_escalated_delta_export_json(delta: Mapping[str, Any] | None) -> str:
    if not isinstance(delta, Mapping):
        return "{}"
    return json.dumps(dict(delta), ensure_ascii=False, indent=2)




def run_escalated_delta_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


