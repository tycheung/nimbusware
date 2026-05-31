from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
)


def security_scan_metadata_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
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
    if not isinstance(payload, Mapping):
        return metrics
    metrics["yaml_key_present"] = (
        payload.get("security_scan_metadata_on_verify_yaml_key_present") is True
    )
    metrics["yaml_parsed_bool"] = payload.get("yaml_parsed_bool") is True
    metrics["effective_enabled"] = payload.get("effective_enabled") is True
    matches = payload.get("security_scan_metadata_yaml_parsed_bool_matches_effective")
    metrics["yaml_matches_effective"] = matches is True
    if matches is False:
        metrics["yaml_effective_mismatch"] = True
    env = payload.get("HERMES_ATTACH_SECURITY_SCAN_METADATA")
    if isinstance(env, dict):
        metrics["env_forces_on"] = env.get("forces_on") is True
        metrics["env_forces_off"] = env.get("forces_off") is True
        metrics["env_unset"] = env.get("unset") is True
    err = payload.get("load_error")
    metrics["load_error_present"] = isinstance(err, str) and bool(err.strip())
    ver = payload.get("workflow_yaml_top_level_version_int")
    if isinstance(ver, int) and not isinstance(ver, bool):
        metrics["workflow_yaml_version_int"] = ver
    raw_bytes = payload.get("workflow_yaml_file_bytes")
    if isinstance(raw_bytes, int) and not isinstance(raw_bytes, bool) and raw_bytes >= 0:
        metrics["workflow_yaml_file_bytes"] = raw_bytes
    return metrics


def security_scan_metadata_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {
            "field": "YAML key present",
            "value": str(metrics.get("yaml_key_present", False)).lower(),
        },
        {
            "field": "YAML parsed bool",
            "value": str(metrics.get("yaml_parsed_bool", False)).lower(),
        },
        {
            "field": "Effective enabled",
            "value": str(metrics.get("effective_enabled", False)).lower(),
        },
        {
            "field": "YAML matches effective",
            "value": str(metrics.get("yaml_matches_effective", True)).lower(),
        },
        {
            "field": "YAML/effective mismatch",
            "value": str(metrics.get("yaml_effective_mismatch", False)).lower(),
        },
        {"field": "Env forces on", "value": str(metrics.get("env_forces_on", False)).lower()},
        {"field": "Env forces off", "value": str(metrics.get("env_forces_off", False)).lower()},
        {"field": "Env unset", "value": str(metrics.get("env_unset", True)).lower()},
    ]
    ver = metrics.get("workflow_yaml_version_int")
    if isinstance(ver, int) and not isinstance(ver, bool):
        rows.append({"field": "Workflow YAML version", "value": str(ver)})
    raw_bytes = metrics.get("workflow_yaml_file_bytes")
    if isinstance(raw_bytes, int) and not isinstance(raw_bytes, bool):
        rows.append({"field": "Workflow YAML bytes", "value": str(raw_bytes)})
    if metrics.get("load_error_present") is True:
        rows.append({"field": "Load error", "value": "yes"})
    return rows


def security_scan_metadata_workflow_explainer_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(metrics)


def security_scan_metadata_workflow_explainer_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


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
    if not parts:
        return None
    return "Security scan metadata explainer metrics: " + ", ".join(parts) + "."


def security_scan_metadata_workflow_explainer_operator_metrics_export_filename_slug() -> str:
    return "security_scan_metadata_workflow_explainer_operator_metrics"
