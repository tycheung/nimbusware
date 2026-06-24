from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from functools import partial
from typing import Any

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
    sequence_export_json,
    table_rows_csv,
)
from nimbusware_console.run_escalated._common import _stringify
from nimbusware_projections.fields.run_escalated import (
    RUN_ESCALATED_DELTA_FIELDS,
    RUN_ESCALATED_DISPLAY_FIELDS,
)


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


def run_escalated_summary_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    return field_value_table_rows_csv(rows)


def run_escalated_export_json(summary: Mapping[str, Any] | None) -> str:
    return mapping_export_json(summary)


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


run_escalated_history_table_rows_csv = partial(
    table_rows_csv, columns=_RUN_ESCALATED_HISTORY_CSV_COLUMNS
)


def run_escalated_history_export_json(history: Sequence[Mapping[str, Any]]) -> str:
    items = [dict(x) for x in history if isinstance(x, Mapping)]
    return sequence_export_json(items)


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


_RUN_ESCALATED_DELTA_FIELDS = RUN_ESCALATED_DELTA_FIELDS


def run_escalated_delta_summary_rows(delta: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not isinstance(delta, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key, label in _RUN_ESCALATED_DELTA_FIELDS:
        if key not in delta:
            continue
        rows.append({"field": label, "value": _stringify(delta.get(key))})
    return rows


run_escalated_delta_table_rows_csv = field_value_table_rows_csv


def run_escalated_delta_export_json(delta: Mapping[str, Any] | None) -> str:
    return mapping_export_json(delta)


def run_escalated_delta_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]
