from __future__ import annotations

from agent_core.coercion import is_strict_int
from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.operator_metrics_exports import (
    build_metrics_fn,
    caption_from_parts,
    install_operator_metrics_module,
    table_rows_fn,
)

_PREFIX = "universal_critique_workflow_explainer"

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


def _caption_parts(metrics: Mapping[str, Any]) -> list[str]:
    if metrics.get("yaml_present") is not True:
        return []
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
    if is_strict_int(lists) and lists > 0:
        parts.append(f"**{lists}** list child(ren)")
    scalar = metrics.get("scalar_leaf_count", 0)
    if is_strict_int(scalar) and scalar > 0:
        parts.append(f"**{scalar}** scalar leaf(es)")
    return parts


(
    universal_critique_workflow_explainer_operator_metrics,
    universal_critique_workflow_explainer_operator_metrics_table_rows,
    universal_critique_workflow_explainer_operator_metrics_caption,
    universal_critique_workflow_explainer_operator_metrics_export_json,
    universal_critique_workflow_explainer_operator_metrics_table_rows_csv,
    universal_critique_workflow_explainer_operator_metrics_export_filename_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix=_PREFIX,
    metrics=build_metrics_fn(
        _DEFAULTS,
        bool_fields=(("universal_critique_yaml_present", "yaml_present"),),
        int_fields=(
            ("universal_critique_yaml_top_level_enabled_true_count", "enabled_true_count"),
            ("universal_critique_yaml_top_level_enabled_false_count", "enabled_false_count"),
            (
                "universal_critique_yaml_top_level_enabled_unset_mapping_count",
                "enabled_unset_mapping_count",
            ),
            ("universal_critique_yaml_top_level_mapping_child_count", "mapping_child_count"),
            ("universal_critique_yaml_top_level_list_child_count", "list_child_count"),
            ("universal_critique_yaml_top_level_scalar_leaf_count", "scalar_leaf_count"),
        ),
        list_len_fields=(("universal_critique_yaml_top_level_keys", "top_level_key_count"),),
        nested_bool_fields=(
            ("yaml_only", (("default_enabled", "default_enabled_on"),)),
            (
                "effective_with_env",
                (
                    ("unanimous_gate_enforce", "unanimous_gate_enforce"),
                    ("fw_enabled", "fw_enabled"),
                    ("mi_enabled", "mi_enabled"),
                ),
            ),
        ),
        load_error=True,
    ),
    table_rows=table_rows_fn(_TABLE_ROWS),
    caption=caption_from_parts("Universal critique explainer metrics: ", _caption_parts),
)
