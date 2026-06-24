from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.operator_metrics_exports import (
    build_metrics_fn,
    caption_from_parts,
    install_operator_metrics_module,
    table_rows_fn,
)

_PREFIX = "self_refinement_workflow_explainer"

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

_OPTIONAL_METRIC_KEYS = frozenset({"merged_max_iterations", "policy_version", "load_error_present"})


def _caption_parts(metrics: Mapping[str, Any]) -> list[str]:
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
    return parts


(
    self_refinement_workflow_explainer_operator_metrics,
    self_refinement_workflow_explainer_operator_metrics_table_rows,
    self_refinement_workflow_explainer_operator_metrics_caption,
    self_refinement_workflow_explainer_operator_metrics_export_json,
    self_refinement_workflow_explainer_operator_metrics_table_rows_csv,
    self_refinement_workflow_explainer_operator_metrics_export_filename_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix=_PREFIX,
    metrics=build_metrics_fn(
        _DEFAULTS,
        bool_fields=(("self_refinement_yaml_present", "yaml_present"),),
        int_fields=(("self_refinement_yaml_mapping_string_key_count", "yaml_mapping_key_count"),),
        nested_bool_fields=(
            ("policy_yaml", (("enabled", "policy_enabled"),)),
            (
                "marker_merge",
                (
                    ("would_emit_self_refinement_marker", "would_emit_marker"),
                    ("would_emit_marker_after_env", "would_emit_marker_after_env"),
                ),
            ),
        ),
        nested_optional_int=(("policy_yaml", "version", "policy_version"),),
        optional_int=(("merged_max_iterations", "merged_max_iterations"),),
        env_tri_state=(
            (
                "NIMBUSWARE_SELF_REFINEMENT_UNGATED_LOOP",
                "ungated_loop_forces_on",
                "ungated_loop_forces_off",
                "ungated_loop_unset",
            ),
        ),
        load_error=True,
    ),
    table_rows=table_rows_fn(
        _TABLE_ROWS,
        include_when=lambda m, key: (
            key not in _OPTIONAL_METRIC_KEYS
            or (key == "load_error_present" and m.get("load_error_present") is True)
            or m.get(key) is not None
        ),
    ),
    caption=caption_from_parts("Self-refinement explainer metrics: ", _caption_parts),
)
