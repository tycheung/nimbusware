from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
)


def universal_critique_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
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
    if not isinstance(payload, Mapping):
        return metrics
    metrics["yaml_present"] = payload.get("universal_critique_yaml_present") is True
    keys = payload.get("universal_critique_yaml_top_level_keys")
    if isinstance(keys, list):
        metrics["top_level_key_count"] = len(keys)

    def _int_field(key: str) -> int:
        raw = payload.get(key)
        if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
            return raw
        return 0

    metrics["enabled_true_count"] = _int_field(
        "universal_critique_yaml_top_level_enabled_true_count",
    )
    metrics["enabled_false_count"] = _int_field(
        "universal_critique_yaml_top_level_enabled_false_count",
    )
    metrics["enabled_unset_mapping_count"] = _int_field(
        "universal_critique_yaml_top_level_enabled_unset_mapping_count",
    )
    metrics["mapping_child_count"] = _int_field(
        "universal_critique_yaml_top_level_mapping_child_count",
    )
    metrics["list_child_count"] = _int_field(
        "universal_critique_yaml_top_level_list_child_count",
    )
    metrics["scalar_leaf_count"] = _int_field(
        "universal_critique_yaml_top_level_scalar_leaf_count",
    )
    yaml_only = payload.get("yaml_only")
    if isinstance(yaml_only, Mapping):
        metrics["default_enabled_on"] = yaml_only.get("default_enabled") is True
    eff = payload.get("effective_with_env")
    if isinstance(eff, Mapping):
        metrics["unanimous_gate_enforce"] = eff.get("unanimous_gate_enforce") is True
        metrics["fw_enabled"] = eff.get("fw_enabled") is True
        metrics["mi_enabled"] = eff.get("mi_enabled") is True
    err = payload.get("load_error")
    metrics["load_error_present"] = isinstance(err, str) and bool(err.strip())
    return metrics


def universal_critique_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    return [
        {"field": "YAML present", "value": str(metrics.get("yaml_present", False)).lower()},
        {"field": "Top-level keys", "value": str(metrics.get("top_level_key_count", 0))},
        {"field": "Enabled true", "value": str(metrics.get("enabled_true_count", 0))},
        {"field": "Enabled false", "value": str(metrics.get("enabled_false_count", 0))},
        {
            "field": "Enabled unset (mapping)",
            "value": str(metrics.get("enabled_unset_mapping_count", 0)),
        },
        {"field": "Mapping children", "value": str(metrics.get("mapping_child_count", 0))},
        {"field": "List children", "value": str(metrics.get("list_child_count", 0))},
        {"field": "Scalar leaves", "value": str(metrics.get("scalar_leaf_count", 0))},
        {
            "field": "default_enabled on",
            "value": str(metrics.get("default_enabled_on", False)).lower(),
        },
        {
            "field": "unanimous_gate_enforce",
            "value": str(metrics.get("unanimous_gate_enforce", False)).lower(),
        },
        {"field": "fw_enabled", "value": str(metrics.get("fw_enabled", False)).lower()},
        {"field": "mi_enabled", "value": str(metrics.get("mi_enabled", False)).lower()},
    ]


def universal_critique_workflow_explainer_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(metrics)


def universal_critique_workflow_explainer_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


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
    lists = metrics.get("list_child_count", 0)
    if isinstance(lists, int) and not isinstance(lists, bool) and lists > 0:
        parts.append(f"**{lists}** list child(ren)")
    return "Universal critique explainer metrics: " + ", ".join(parts) + "."


def universal_critique_workflow_explainer_operator_metrics_export_filename_slug() -> str:
    return "universal_critique_workflow_explainer_operator_metrics"
