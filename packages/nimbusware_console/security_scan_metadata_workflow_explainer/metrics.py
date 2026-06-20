from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.metrics_scaffold import (
    apply_bool_payload_fields,
    apply_env_tri_state_metrics,
    apply_load_error_present,
    apply_workflow_yaml_file_metrics,
    default_operator_metrics,
    metrics_caption,
    metrics_table_rows,
)
from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports

_DEFAULTS: dict[str, Any] = {
    "yaml_key_present": False,
    "yaml_parsed_bool": False,
    "effective_enabled": False,
    "yaml_matches_effective": True,
    "yaml_effective_mismatch": False,
    "env_forces_on": False,
    "env_forces_off": False,
    "env_unset": True,
    "load_error_present": False,
    "workflow_yaml_version_int": None,
    "workflow_yaml_file_bytes": None,
}

_BOOL_FIELDS: tuple[tuple[str, str], ...] = (
    ("security_scan_metadata_on_verify_yaml_key_present", "yaml_key_present"),
    ("yaml_parsed_bool", "yaml_parsed_bool"),
    ("effective_enabled", "effective_enabled"),
)

_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("YAML key present", "yaml_key_present"),
    ("YAML parsed bool", "yaml_parsed_bool"),
    ("Effective enabled", "effective_enabled"),
    ("YAML matches effective", "yaml_matches_effective"),
    ("YAML/effective mismatch", "yaml_effective_mismatch"),
    ("Env forces on", "env_forces_on"),
    ("Env forces off", "env_forces_off"),
    ("Env unset", "env_unset"),
    ("Workflow YAML version", "workflow_yaml_version_int"),
    ("Workflow YAML bytes", "workflow_yaml_file_bytes"),
    ("Load error", "load_error_present"),
)


def security_scan_metadata_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics = default_operator_metrics(_DEFAULTS)
    if not isinstance(payload, Mapping):
        return metrics
    apply_bool_payload_fields(metrics, payload, _BOOL_FIELDS)
    matches = payload.get("security_scan_metadata_yaml_parsed_bool_matches_effective")
    metrics["yaml_matches_effective"] = matches is True
    if matches is False:
        metrics["yaml_effective_mismatch"] = True
    apply_env_tri_state_metrics(
        metrics,
        payload,
        "NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA",
    )
    apply_load_error_present(metrics, payload)
    apply_workflow_yaml_file_metrics(metrics, payload)
    return metrics


def security_scan_metadata_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    rows = metrics_table_rows(
        metrics,
        [r for r in _TABLE_ROWS if r[1] != "load_error_present"],
    )
    if isinstance(metrics, Mapping) and metrics.get("load_error_present") is True:
        rows.append({"field": "Load error", "value": "yes"})
    return rows


def security_scan_metadata_workflow_explainer_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    parts: list[str] = []
    if metrics.get("yaml_matches_effective") is False:
        parts.append("YAML vs effective **mismatch**")
    if metrics.get("env_forces_on") is True:
        parts.append("env **forces on**")
    elif metrics.get("env_forces_off") is True:
        parts.append("env **forces off**")
    if metrics.get("effective_enabled") is True:
        parts.append("effective **enabled**")
    elif metrics.get("yaml_parsed_bool") is False and metrics.get("yaml_key_present") is True:
        parts.append("effective **disabled**")
    raw_bytes = metrics.get("workflow_yaml_file_bytes")
    if isinstance(raw_bytes, int) and not isinstance(raw_bytes, bool) and raw_bytes > 0:
        parts.append(f"workflow YAML **{raw_bytes}** byte(s)")
    if metrics.get("load_error_present") is True:
        parts.append("load error")
    return metrics_caption("Security scan metadata explainer metrics: ", parts)


(
    security_scan_metadata_workflow_explainer_operator_metrics_export_json,
    security_scan_metadata_workflow_explainer_operator_metrics_table_rows_csv,
    security_scan_metadata_workflow_explainer_operator_metrics_export_filename_slug,
) = bind_operator_metrics_exports(
    export_slug="security_scan_metadata_workflow_explainer_operator_metrics",
)
