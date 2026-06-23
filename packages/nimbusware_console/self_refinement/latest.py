from __future__ import annotations

import csv
import json
import re
from collections.abc import Mapping, Sequence
from io import StringIO
from typing import Any

from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports
from nimbusware_console.self_refinement._helpers import (
    _SELF_REFINEMENT_FIELDS,
    _stringify,
)


def self_refinement_summary_rows(sr: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not sr:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _SELF_REFINEMENT_FIELDS:
        if key not in sr:
            continue
        rows.append({"field": label, "value": _stringify(sr.get(key))})
    return rows


_SELF_REFINEMENT_LATEST_SUMMARY_CSV_COLUMNS: tuple[str, ...] = ("field", "value")


def self_refinement_latest_summary_rows_csv(rows: Sequence[Mapping[str, str]]) -> str:
    if not rows:
        return ""
    buf = StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=list(_SELF_REFINEMENT_LATEST_SUMMARY_CSV_COLUMNS),
        extrasaction="ignore",
    )
    w.writeheader()
    for r in rows:
        if isinstance(r, Mapping):
            w.writerow(
                {k: r.get(k, "") for k in _SELF_REFINEMENT_LATEST_SUMMARY_CSV_COLUMNS},
            )
    return buf.getvalue()


def self_refinement_latest_export_json(sr: Mapping[str, Any] | None) -> str:
    if not isinstance(sr, Mapping):
        return "{}"
    return json.dumps(dict(sr), ensure_ascii=False, indent=2)


def self_refinement_latest_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    raw = str(run_id).strip().lower()
    slug = re.sub(r"[^a-z0-9_.-]+", "_", raw).strip("._-") or "run"
    return slug[:max_len]


(
    _self_refinement_timeline_operator_metrics_export_json_impl,
    self_refinement_timeline_operator_metrics_table_rows_csv,
    _self_refinement_timeline_operator_metrics_exports_slug,
) = bind_operator_metrics_exports(export_slug="self_refinement_timeline_operator_metrics")


def self_refinement_timeline_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping) or not metrics.get("present"):
        return "{}"
    return _self_refinement_timeline_operator_metrics_export_json_impl(metrics)


def self_refinement_timeline_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return self_refinement_latest_export_filename_slug(run_id, max_len=max_len)


_TIMELINE_DESC_PREVIEW_MAX = 240
