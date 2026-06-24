from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
)
from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports
from nimbusware_console.explainer_core.workflow_exports import run_id_export_filename_slug
from nimbusware_console.integrator_gate._helpers import (
    _INTEGRATOR_GATE_FIELDS,
    _stringify,
)

(
    _integrator_gate_latest_operator_metrics_export_json_impl,
    integrator_gate_latest_operator_metrics_table_rows_csv,
    _integrator_gate_latest_operator_metrics_exports_slug,
) = bind_operator_metrics_exports(export_slug="integrator_gate_latest_operator_metrics")


def integrator_gate_latest_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping) or not metrics.get("present"):
        return "{}"
    return _integrator_gate_latest_operator_metrics_export_json_impl(metrics)


def integrator_gate_latest_operator_metrics_export_filename_slug(
    run_id: str,
    *,
    max_len: int = 36,
) -> str:
    return integrator_gate_latest_export_filename_slug(run_id, max_len=max_len)


(
    _integrator_gate_delta_operator_metrics_export_json_impl,
    integrator_gate_delta_operator_metrics_table_rows_csv,
    _integrator_gate_delta_operator_metrics_exports_slug,
) = bind_operator_metrics_exports(export_slug="integrator_gate_delta_operator_metrics")


def integrator_gate_delta_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    if not isinstance(metrics, Mapping) or not metrics.get("present"):
        return "{}"
    return _integrator_gate_delta_operator_metrics_export_json_impl(metrics)


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


def integrator_gate_delta_summary_rows(delta: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not delta:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _DELTA_FIELDS:
        if key not in delta:
            continue
        rows.append({"field": label, "value": _stringify(delta.get(key))})
    return rows


integrator_gate_delta_summary_rows_csv = field_value_table_rows_csv


def integrator_gate_delta_export_json(delta: Mapping[str, Any] | None) -> str:
    return mapping_export_json(delta)


def integrator_gate_delta_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    return run_id_export_filename_slug(run_id, max_len=max_len)


def integrator_gate_summary_rows(ig: Mapping[str, Any] | None) -> list[dict[str, str]]:
    if not ig:
        return []
    rows: list[dict[str, str]] = []
    for key, label in _INTEGRATOR_GATE_FIELDS:
        if key not in ig:
            continue
        rows.append({"field": label, "value": _stringify(ig.get(key))})
    return rows


integrator_gate_latest_summary_rows_csv = field_value_table_rows_csv


def integrator_gate_latest_export_json(ig: Mapping[str, Any] | None) -> str:
    return mapping_export_json(ig)


def integrator_gate_latest_export_filename_slug(run_id: str, *, max_len: int = 36) -> str:
    return run_id_export_filename_slug(run_id, max_len=max_len)
