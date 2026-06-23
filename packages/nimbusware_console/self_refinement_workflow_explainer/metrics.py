from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.metrics_scaffold import (
    apply_bool_payload_fields,
    apply_env_tri_state_metrics,
    apply_load_error_present,
    apply_nonneg_int_fields,
    apply_optional_int_field,
    default_operator_metrics,
    metrics_caption,
    metrics_table_rows,
)
from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports

_DEFAULTS: dict[str, Any] = {
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

_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("YAML present", "yaml_present"),
    ("YAML mapping keys", "yaml_mapping_key_count"),
    ("Policy enabled", "policy_enabled"),
    ("Would emit marker", "would_emit_marker"),
    ("Would emit after env", "would_emit_marker_after_env"),
    ("Merged max iterations", "merged_max_iterations"),
    ("Ungated loop forces on", "ungated_loop_forces_on"),
    ("Ungated loop forces off", "ungated_loop_forces_off"),
    ("Policy version", "policy_version"),
    ("Load error", "load_error_present"),
)


def self_refinement_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics = default_operator_metrics(_DEFAULTS)
    if not isinstance(payload, Mapping):
        return metrics
    apply_bool_payload_fields(
        metrics,
        payload,
        (("self_refinement_yaml_present", "yaml_present"),),
    )
    apply_nonneg_int_fields(
        metrics,
        payload,
        (("self_refinement_yaml_mapping_string_key_count", "yaml_mapping_key_count"),),
    )
    pol = payload.get("policy_yaml")
    if isinstance(pol, dict):
        metrics["policy_enabled"] = pol.get("enabled") is True
        apply_optional_int_field(metrics, pol, "version", "policy_version")
    mm = payload.get("marker_merge")
    if isinstance(mm, dict):
        apply_bool_payload_fields(
            metrics,
            mm,
            (
                ("would_emit_self_refinement_marker", "would_emit_marker"),
                ("would_emit_marker_after_env", "would_emit_marker_after_env"),
            ),
        )
    apply_optional_int_field(metrics, payload, "merged_max_iterations", "merged_max_iterations")
    apply_env_tri_state_metrics(
        metrics,
        payload,
        "NIMBUSWARE_SELF_REFINEMENT_UNGATED_LOOP",
        forces_on_key="ungated_loop_forces_on",
        forces_off_key="ungated_loop_forces_off",
        unset_key="ungated_loop_unset",
    )
    apply_load_error_present(metrics, payload)
    return metrics


def self_refinement_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return metrics_table_rows(
        metrics,
        _TABLE_ROWS,
        include_when=lambda m, key: (
            key
            not in {"merged_max_iterations", "policy_version", "load_error_present"}
            or (
                key == "load_error_present"
                and m.get("load_error_present") is True
            )
            or m.get(key) is not None
        ),
    )


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
    if metrics.get("load_error_present") is True:
        parts.append("load error")
    return metrics_caption("Self-refinement explainer metrics: ", parts)


(
    self_refinement_workflow_explainer_operator_metrics_export_json,
    self_refinement_workflow_explainer_operator_metrics_table_rows_csv,
    self_refinement_workflow_explainer_operator_metrics_export_filename_slug,
) = bind_operator_metrics_exports(
    export_slug="self_refinement_workflow_explainer_operator_metrics",
)
