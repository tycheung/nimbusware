from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
)
from nimbusware_console.explainer_core.operator_metrics_exports import install_named_operator_metrics_exports
from nimbusware_console.explainer_core.workflow_exports import run_id_export_filename_slug
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


self_refinement_latest_summary_rows_csv = field_value_table_rows_csv


def self_refinement_latest_export_json(sr: Mapping[str, Any] | None) -> str:
    return mapping_export_json(sr)


def self_refinement_latest_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return run_id_export_filename_slug(run_id, max_len=max_len)


(
    _self_refinement_timeline_operator_metrics_export_json_impl,
    self_refinement_timeline_operator_metrics_table_rows_csv,
    _self_refinement_timeline_operator_metrics_exports_slug,
) = install_named_operator_metrics_exports(
    globals(),
    "self_refinement_timeline",
    export_slug="self_refinement_timeline_operator_metrics",
)


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
