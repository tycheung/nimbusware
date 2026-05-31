from __future__ import annotations

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
    table_rows_csv,
)
import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from nimbusware_console.integrator_gate._helpers import (
    _INTEGRATOR_GATE_FIELDS,
    _optional_float,
    _stringify,
    integrator_gate_from_timeline,
    integrator_gate_history_from_timeline,
)
from nimbusware_console.integrator_gate.history import (
    integrator_gate_history_operator_metrics,
)
def integrator_gate_latest_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping) or not metrics.get("present"):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def integrator_gate_latest_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


def integrator_gate_latest_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return integrator_gate_latest_export_filename_slug(run_id, max_len=max_len)



def integrator_gate_delta_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping) or not metrics.get("present"):
        return "{}"
    return json.dumps(dict(metrics), indent=2, ensure_ascii=False)


def integrator_gate_delta_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


def integrator_gate_delta_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return integrator_gate_delta_export_filename_slug(run_id, max_len=max_len)


def integrator_gate_delta_from_timeline(
    timeline_body: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(timeline_body, Mapping):
        return None
    raw = timeline_body.get("integrator_gate_delta")
    return raw if isinstance(raw, dict) else None


_DELTA_FIELDS: tuple[tuple[str, str], ...] = (
    ("integrator_score_delta", "Score delta (current − prior)"),
    ("verdict_changed", "Verdict changed"),
    ("bundle_id_changed", "Bundle id changed"),
    ("previous_verdict", "Previous verdict"),
    ("current_verdict", "Current verdict"),
    ("min_score_to_pass", "Min score to pass (current gate)"),
    ("previous_event_id", "Previous event id"),
    ("current_event_id", "Current event id"),
)

_INTEGRATOR_GATE_DELTA_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def integrator_gate_delta_summary_rows(delta: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not delta:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _DELTA_FIELDS:
        if key not in delta:
            continue
        rows.append({"field": label, "value": _stringify(delta.get(key))})
    return rows



def integrator_gate_delta_summary_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_INTEGRATOR_GATE_DELTA_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _INTEGRATOR_GATE_DELTA_SUMMARY_CSV_COLUMNS},
            )
    return buf.getvalue()


def integrator_gate_delta_export_json(delta: Mapping[str, Any] | None) -> str:
    if not isinstance(delta, Mapping):
        return "{}"
    return json.dumps(dict(delta), ensure_ascii=False, indent=2)


def integrator_gate_delta_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


def integrator_gate_summary_rows(ig: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not ig:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _INTEGRATOR_GATE_FIELDS:
        if key not in ig:
            continue
        rows.append({"field": label, "value": _stringify(ig.get(key))})
    return rows


_INTEGRATOR_GATE_LATEST_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def integrator_gate_latest_summary_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_INTEGRATOR_GATE_LATEST_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _INTEGRATOR_GATE_LATEST_SUMMARY_CSV_COLUMNS},
            )
    return buf.getvalue()


def integrator_gate_latest_export_json(ig: Mapping[str, Any] | None) -> str:
    if not isinstance(ig, Mapping):
        return "{}"
    return json.dumps(dict(ig), ensure_ascii=False, indent=2)


def integrator_gate_latest_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


