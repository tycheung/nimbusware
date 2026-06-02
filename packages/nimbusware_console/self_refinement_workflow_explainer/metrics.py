from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
)


def self_refinement_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "yaml_present": False,
        "yaml_mapping_key_count": 0,
        "policy_enabled": False,
        "policy_version": None,
        "would_emit_marker": False,
        "would_emit_marker_after_env": False,
        "merged_max_iterations": None,
        "ungated_loop_forces_on": False,
        "ungated_loop_forces_off": False,
        "ungated_loop_unset": True,
        "load_error_present": False,
    }
    if not isinstance(payload, Mapping):
        return metrics
    metrics["yaml_present"] = payload.get("self_refinement_yaml_present") is True
    raw_kc = payload.get("self_refinement_yaml_mapping_string_key_count")
    if isinstance(raw_kc, int) and not isinstance(raw_kc, bool) and raw_kc >= 0:
        metrics["yaml_mapping_key_count"] = raw_kc
    pol = payload.get("policy_yaml")
    if isinstance(pol, dict):
        metrics["policy_enabled"] = pol.get("enabled") is True
        ver = pol.get("version")
        if isinstance(ver, int) and not isinstance(ver, bool):
            metrics["policy_version"] = ver
    mm = payload.get("marker_merge")
    if isinstance(mm, dict):
        metrics["would_emit_marker"] = mm.get("would_emit_self_refinement_marker") is True
        metrics["would_emit_marker_after_env"] = mm.get("would_emit_marker_after_env") is True
    merged = payload.get("merged_max_iterations")
    if isinstance(merged, int) and not isinstance(merged, bool) and merged >= 0:
        metrics["merged_max_iterations"] = merged
    ul = payload.get("HERMES_SELF_REFINEMENT_UNGATED_LOOP")
    if isinstance(ul, dict):
        metrics["ungated_loop_forces_on"] = ul.get("forces_on") is True
        metrics["ungated_loop_forces_off"] = ul.get("forces_off") is True
        metrics["ungated_loop_unset"] = ul.get("unset") is True
    err = payload.get("load_error")
    metrics["load_error_present"] = isinstance(err, str) and bool(err.strip())
    return metrics


def self_refinement_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {"field": "YAML present", "value": str(metrics.get("yaml_present", False)).lower()},
        {
            "field": "YAML mapping keys",
            "value": str(metrics.get("yaml_mapping_key_count", 0)),
        },
        {"field": "Policy enabled", "value": str(metrics.get("policy_enabled", False)).lower()},
        {
            "field": "Would emit marker",
            "value": str(metrics.get("would_emit_marker", False)).lower(),
        },
        {
            "field": "Would emit after env",
            "value": str(metrics.get("would_emit_marker_after_env", False)).lower(),
        },
    ]
    merged = metrics.get("merged_max_iterations")
    if isinstance(merged, int) and not isinstance(merged, bool):
        rows.append({"field": "Merged max iterations", "value": str(merged)})
    rows.extend(
        [
            {
                "field": "Ungated loop forces on",
                "value": str(metrics.get("ungated_loop_forces_on", False)).lower(),
            },
            {
                "field": "Ungated loop forces off",
                "value": str(metrics.get("ungated_loop_forces_off", False)).lower(),
            },
        ]
    )
    merged_max = metrics.get("merged_max_iterations")
    if isinstance(merged_max, int) and not isinstance(merged_max, bool):
        rows.append({"field": "Merged max iterations", "value": str(merged_max)})
    ver = metrics.get("policy_version")
    if isinstance(ver, int) and not isinstance(ver, bool):
        rows.append({"field": "Policy version", "value": str(ver)})
    if metrics.get("load_error_present") is True:
        rows.append({"field": "Load error", "value": "yes"})
    return rows


def self_refinement_workflow_explainer_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(metrics)


def self_refinement_workflow_explainer_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


def self_refinement_workflow_explainer_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    parts: list[str] = []
    if metrics.get("would_emit_marker_after_env") is True:
        parts.append("marker **would emit** (after env)")
    elif metrics.get("would_emit_marker") is True:
        parts.append("marker **would emit**")
    if metrics.get("ungated_loop_forces_on") is True:
        parts.append("ungated loop env **forces on**")
    elif metrics.get("ungated_loop_forces_off") is True:
        parts.append("ungated loop env **forces off**")
    if metrics.get("policy_enabled") is True:
        parts.append("policy enabled")
    merged_max = metrics.get("merged_max_iterations")
    if isinstance(merged_max, int) and not isinstance(merged_max, bool):
        parts.append(f"max iterations **{merged_max}**")
    elif metrics.get("yaml_present") is True:
        parts.append("YAML block present")
    merged_max = metrics.get("merged_max_iterations")
    if isinstance(merged_max, int) and not isinstance(merged_max, bool):
        parts.append(f"max iterations **{merged_max}**")
    if metrics.get("load_error_present") is True:
        parts.append("load error")
    if not parts:
        return None
    return "Self-refinement explainer metrics: " + ", ".join(parts) + "."
