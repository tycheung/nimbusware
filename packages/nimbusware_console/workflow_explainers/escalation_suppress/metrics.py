from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.operator_metrics_exports import (
    build_metrics_fn,
    caption_from_parts,
    install_operator_metrics_module,
    table_rows_fn,
)

_PREFIX = "escalation_suppress_workflow_explainer"

_DEFAULTS: dict[str, Any] = {
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

_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("Escalation key present", "escalation_key_present"),
    ("Suppress automatic (effective)", "suppress_automatic_escalation_effective"),
    ("Policy YAML exists", "policy_yaml_exists"),
    ("Policy top-level keys", "policy_top_level_key_count"),
    ("anti_deadlock mapping", "anti_deadlock_mapping_present"),
    ("anti_deadlock enabled", "anti_deadlock_enabled"),
    ("anti_deadlock min_progress_events", "anti_deadlock_min_progress_events"),
    ("Policy YAML bytes", "policy_yaml_file_bytes"),
    ("Policy YAML age (s)", "policy_yaml_age_seconds"),
)

_OPTIONAL_METRIC_KEYS = frozenset(
    {
        "anti_deadlock_min_progress_events",
        "policy_yaml_file_bytes",
        "policy_yaml_age_seconds",
    }
)


def _caption_parts(metrics: Mapping[str, Any]) -> list[str]:
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
    return parts


(
    escalation_suppress_workflow_explainer_operator_metrics,
    escalation_suppress_workflow_explainer_operator_metrics_table_rows,
    escalation_suppress_workflow_explainer_operator_metrics_caption,
    escalation_suppress_workflow_explainer_operator_metrics_export_json,
    escalation_suppress_workflow_explainer_operator_metrics_table_rows_csv,
    escalation_suppress_workflow_explainer_operator_metrics_export_filename_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix=_PREFIX,
    metrics=build_metrics_fn(
        _DEFAULTS,
        bool_fields=(
            ("escalation_yaml_key_present", "escalation_key_present"),
            ("suppress_automatic_escalation_effective", "suppress_automatic_escalation_effective"),
            ("escalation_policy_yaml_path_exists", "policy_yaml_exists"),
            ("escalation_policy_yaml_has_anti_deadlock_mapping", "anti_deadlock_mapping_present"),
            ("escalation_policy_yaml_anti_deadlock_enabled", "anti_deadlock_enabled"),
        ),
        int_fields=(
            ("escalation_policy_yaml_top_level_key_count", "policy_top_level_key_count"),
            ("escalation_policy_yaml_file_bytes", "policy_yaml_file_bytes"),
            ("escalation_policy_yaml_age_seconds", "policy_yaml_age_seconds"),
        ),
        optional_int=(
            (
                "escalation_policy_yaml_anti_deadlock_min_progress_events",
                "anti_deadlock_min_progress_events",
            ),
        ),
        load_error=True,
    ),
    table_rows=table_rows_fn(
        _TABLE_ROWS,
        include_when=lambda m, key: key not in _OPTIONAL_METRIC_KEYS or m.get(key) is not None,
    ),
    caption=caption_from_parts("Escalation suppress explainer metrics: ", _caption_parts),
)
