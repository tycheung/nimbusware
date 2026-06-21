from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.metrics_scaffold import (
    apply_bool_payload_fields,
    apply_load_error_present,
    apply_nested_bool_fields,
    apply_nonneg_int_fields,
    default_operator_metrics,
    metrics_caption,
    metrics_table_rows,
)
from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports

_DEFAULTS: dict[str, Any] = {
    "yaml_present": False,
    "top_level_key_count": 0,
    "enabled_true_count": 0,
    "enabled_false_count": 0,
    "enabled_unset_mapping_count": 0,
    "mapping_child_count": 0,
    "scalar_leaf_count": 0,
    "list_child_count": 0,
    "default_enabled_on": False,
    "unanimous_gate_enforce": False,
    "fw_enabled": False,
    "mi_enabled": False,
    "load_error_present": False,
}

_BOOL_FIELDS: tuple[tuple[str, str], ...] = (("universal_critique_yaml_present", "yaml_present"),)

_INT_FIELDS: tuple[tuple[str, str], ...] = (
    ("universal_critique_yaml_top_level_enabled_true_count", "enabled_true_count"),
    ("universal_critique_yaml_top_level_enabled_false_count", "enabled_false_count"),
    (
        "universal_critique_yaml_top_level_enabled_unset_mapping_count",
        "enabled_unset_mapping_count",
    ),
    ("universal_critique_yaml_top_level_mapping_child_count", "mapping_child_count"),
    ("universal_critique_yaml_top_level_list_child_count", "list_child_count"),
    ("universal_critique_yaml_top_level_scalar_leaf_count", "scalar_leaf_count"),
)

_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("YAML present", "yaml_present"),
    ("Top-level keys", "top_level_key_count"),
    ("Enabled true", "enabled_true_count"),
    ("Enabled false", "enabled_false_count"),
    ("Enabled unset (mapping)", "enabled_unset_mapping_count"),
    ("Mapping children", "mapping_child_count"),
    ("List children", "list_child_count"),
    ("Scalar leaves", "scalar_leaf_count"),
    ("default_enabled on", "default_enabled_on"),
    ("unanimous_gate_enforce", "unanimous_gate_enforce"),
    ("fw_enabled", "fw_enabled"),
    ("mi_enabled", "mi_enabled"),
)


def universal_critique_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics = default_operator_metrics(_DEFAULTS)
    if not isinstance(payload, Mapping):
        return metrics
    apply_bool_payload_fields(metrics, payload, _BOOL_FIELDS)
    keys = payload.get("universal_critique_yaml_top_level_keys")
    if isinstance(keys, list):
        metrics["top_level_key_count"] = len(keys)
    apply_nonneg_int_fields(metrics, payload, _INT_FIELDS)
    apply_nested_bool_fields(
        metrics,
        payload,
        "yaml_only",
        (("default_enabled", "default_enabled_on"),),
    )
    apply_nested_bool_fields(
        metrics,
        payload,
        "effective_with_env",
        (
            ("unanimous_gate_enforce", "unanimous_gate_enforce"),
            ("fw_enabled", "fw_enabled"),
            ("mi_enabled", "mi_enabled"),
        ),
    )
    apply_load_error_present(metrics, payload)
    return metrics


def universal_critique_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return metrics_table_rows(metrics, _TABLE_ROWS)


def universal_critique_workflow_explainer_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("yaml_present") is not True:
        return None
    nkeys = metrics.get("top_level_key_count", 0)
    if not isinstance(nkeys, int) or isinstance(nkeys, bool):
        nkeys = 0
    enabled = metrics.get("enabled_true_count", 0)
    if not isinstance(enabled, int) or isinstance(enabled, bool):
        enabled = 0
    parts = [
        f"**{nkeys}** stage key(s)",
        f"**{enabled}** with ``enabled: true``",
    ]
    if metrics.get("default_enabled_on") is True:
        parts.append("``default_enabled`` **on**")
    if metrics.get("unanimous_gate_enforce") is True:
        parts.append("unanimous gate **on**")
    if metrics.get("fw_enabled") is True:
        parts.append("fw panel **on**")
    if metrics.get("mi_enabled") is True:
        parts.append("mi panel **on**")
    lists = metrics.get("list_child_count", 0)
    if isinstance(lists, int) and not isinstance(lists, bool) and lists > 0:
        parts.append(f"**{lists}** list child(ren)")
    scalar = metrics.get("scalar_leaf_count", 0)
    if isinstance(scalar, int) and not isinstance(scalar, bool) and scalar > 0:
        parts.append(f"**{scalar}** scalar leaf(es)")
    return metrics_caption("Universal critique explainer metrics: ", parts)


(
    universal_critique_workflow_explainer_operator_metrics_export_json,
    universal_critique_workflow_explainer_operator_metrics_table_rows_csv,
    universal_critique_workflow_explainer_operator_metrics_export_filename_slug,
) = bind_operator_metrics_exports(
    export_slug="universal_critique_workflow_explainer_operator_metrics",
)
