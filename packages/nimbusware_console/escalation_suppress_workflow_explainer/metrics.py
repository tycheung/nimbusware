from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
)


def escalation_suppress_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "escalation_key_present": False,
        "suppress_automatic_escalation_effective": False,
        "policy_yaml_exists": False,
        "policy_top_level_key_count": 0,
        "anti_deadlock_mapping_present": False,
        "anti_deadlock_enabled": False,
        "anti_deadlock_min_progress_events": None,
        "policy_yaml_file_bytes": None,
        "policy_yaml_age_seconds": None,
        "load_error_present": False,
    }
    if not isinstance(payload, Mapping):
        return metrics
    metrics["escalation_key_present"] = payload.get("escalation_yaml_key_present") is True
    metrics["suppress_automatic_escalation_effective"] = (
        payload.get("suppress_automatic_escalation_effective") is True
    )
    metrics["policy_yaml_exists"] = payload.get("escalation_policy_yaml_path_exists") is True
    raw_kc = payload.get("escalation_policy_yaml_top_level_key_count")
    if isinstance(raw_kc, int) and not isinstance(raw_kc, bool) and raw_kc >= 0:
        metrics["policy_top_level_key_count"] = raw_kc
    metrics["anti_deadlock_mapping_present"] = (
        payload.get("escalation_policy_yaml_has_anti_deadlock_mapping") is True
    )
    if payload.get("escalation_policy_yaml_anti_deadlock_enabled") is True:
        metrics["anti_deadlock_enabled"] = True
    raw_mp = payload.get("escalation_policy_yaml_anti_deadlock_min_progress_events")
    if isinstance(raw_mp, int) and not isinstance(raw_mp, bool) and raw_mp >= 0:
        metrics["anti_deadlock_min_progress_events"] = raw_mp
    raw_bytes = payload.get("escalation_policy_yaml_file_bytes")
    if isinstance(raw_bytes, int) and not isinstance(raw_bytes, bool) and raw_bytes >= 0:
        metrics["policy_yaml_file_bytes"] = raw_bytes
    age = payload.get("escalation_policy_yaml_age_seconds")
    if isinstance(age, int) and not isinstance(age, bool) and age >= 0:
        metrics["policy_yaml_age_seconds"] = age
    err = payload.get("load_error")
    metrics["load_error_present"] = isinstance(err, str) and bool(err.strip())
    return metrics


def escalation_suppress_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {
            "field": "Escalation key present",
            "value": str(metrics.get("escalation_key_present", False)).lower(),
        },
        {
            "field": "Suppress automatic (effective)",
            "value": str(
                metrics.get("suppress_automatic_escalation_effective", False),
            ).lower(),
        },
        {
            "field": "Policy YAML exists",
            "value": str(metrics.get("policy_yaml_exists", False)).lower(),
        },
        {
            "field": "Policy top-level keys",
            "value": str(metrics.get("policy_top_level_key_count", 0)),
        },
        {
            "field": "anti_deadlock mapping",
            "value": str(metrics.get("anti_deadlock_mapping_present", False)).lower(),
        },
        {
            "field": "anti_deadlock enabled",
            "value": str(metrics.get("anti_deadlock_enabled", False)).lower(),
        },
    ]
    mp = metrics.get("anti_deadlock_min_progress_events")
    if isinstance(mp, int) and not isinstance(mp, bool):
        rows.append(
            {"field": "anti_deadlock min_progress_events", "value": str(mp)},
        )
    raw_bytes = metrics.get("policy_yaml_file_bytes")
    if isinstance(raw_bytes, int) and not isinstance(raw_bytes, bool):
        rows.append({"field": "Policy YAML bytes", "value": str(raw_bytes)})
    age = metrics.get("policy_yaml_age_seconds")
    if isinstance(age, int) and not isinstance(age, bool):
        rows.append({"field": "Policy YAML age (s)", "value": str(age)})
    return rows


def escalation_suppress_workflow_explainer_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(metrics)


def escalation_suppress_workflow_explainer_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


def escalation_suppress_workflow_explainer_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    parts: list[str] = []
    if metrics.get("suppress_automatic_escalation_effective") is True:
        parts.append("suppress automatic **on**")
    else:
        parts.append("suppress automatic **off**")
    if metrics.get("policy_yaml_exists") is True:
        parts.append("policy file present")
    else:
        parts.append("policy file missing")
    if metrics.get("anti_deadlock_mapping_present") is True:
        mp = metrics.get("anti_deadlock_min_progress_events")
        if isinstance(mp, int) and not isinstance(mp, bool):
            parts.append(f"anti_deadlock min_progress **{mp}**")
        elif metrics.get("anti_deadlock_enabled") is True:
            parts.append("anti_deadlock **enabled**")
    age = metrics.get("policy_yaml_age_seconds")
    if isinstance(age, int) and not isinstance(age, bool):
        parts.append(f"policy age **{age}s**")
    raw_bytes = metrics.get("policy_yaml_file_bytes")
    if isinstance(raw_bytes, int) and not isinstance(raw_bytes, bool) and raw_bytes > 0:
        parts.append(f"policy YAML **{raw_bytes}** byte(s)")
    if metrics.get("load_error_present") is True:
        parts.append("load error")
    return "Escalation suppress explainer metrics: " + ", ".join(parts) + "."


def escalation_suppress_workflow_explainer_operator_metrics_export_filename_slug() -> str:
    return "escalation_suppress_workflow_explainer_operator_metrics"
