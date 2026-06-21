from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.metrics_scaffold import (
    apply_bool_payload_fields,
    apply_env_flag_metric,
    apply_env_tri_state_metrics,
    apply_load_error_present,
    apply_nonneg_int_fields,
    apply_optional_int_field,
    apply_str_present,
    default_operator_metrics,
    metrics_caption,
    metrics_table_rows,
)
from nimbusware_console.explainer_core.operator_metrics_exports import bind_operator_metrics_exports

_DEFAULTS: dict[str, Any] = {
    "yaml_key_present": False,
    "yaml_parsed_enabled": False,
    "llm_evaluation_enabled": False,
    "would_emit_llm_evaluation": False,
    "would_emit_stage_started": False,
    "env_forces_on": False,
    "env_forces_off": False,
    "env_unset": True,
    "auto_promote_disabled": False,
    "auto_create_disabled": False,
    "persona_id_present": False,
    "yaml_true_bool_value_count": 0,
    "yaml_false_bool_value_count": 0,
    "load_error_present": False,
    "workflow_yaml_version_int": None,
}

_BOOL_FIELDS: tuple[tuple[str, str], ...] = (
    ("agent_evaluator_yaml_key_present", "yaml_key_present"),
    ("yaml_parsed_enabled", "yaml_parsed_enabled"),
    ("yaml_parsed_llm_evaluation_enabled", "llm_evaluation_enabled"),
    ("would_emit_stage_started", "would_emit_stage_started"),
    ("would_emit_llm_evaluation", "would_emit_llm_evaluation"),
)

_INT_FIELDS: tuple[tuple[str, str], ...] = (
    ("agent_evaluator_yaml_true_bool_value_count", "yaml_true_bool_value_count"),
    ("agent_evaluator_yaml_false_bool_value_count", "yaml_false_bool_value_count"),
)

_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("YAML key present", "yaml_key_present"),
    ("YAML parsed enabled", "yaml_parsed_enabled"),
    ("Would emit stage", "would_emit_stage_started"),
    ("Env forces on", "env_forces_on"),
    ("Env forces off", "env_forces_off"),
    ("Env unset", "env_unset"),
    ("Persona id present", "persona_id_present"),
    ("LLM evaluation enabled", "llm_evaluation_enabled"),
    ("Would emit LLM branch", "would_emit_llm_evaluation"),
    ("Auto-promote disabled (env)", "auto_promote_disabled"),
    ("Auto-create disabled (env)", "auto_create_disabled"),
    ("YAML true bool count", "yaml_true_bool_value_count"),
    ("YAML false bool count", "yaml_false_bool_value_count"),
    ("Workflow YAML version", "workflow_yaml_version_int"),
)


def agent_evaluator_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics = default_operator_metrics(_DEFAULTS)
    if not isinstance(payload, Mapping):
        return metrics
    apply_bool_payload_fields(metrics, payload, _BOOL_FIELDS)
    apply_env_tri_state_metrics(metrics, payload, "NIMBUSWARE_AGENT_EVALUATOR")
    apply_env_flag_metric(
        metrics,
        payload,
        "NIMBUSWARE_AGENT_EVALUATOR_AUTO_PROMOTE",
        "disables_auto_promote",
        "auto_promote_disabled",
    )
    apply_env_flag_metric(
        metrics,
        payload,
        "NIMBUSWARE_AGENT_EVALUATOR_AUTO_CREATE",
        "disables_auto_create",
        "auto_create_disabled",
    )
    apply_str_present(metrics, payload, "yaml_parsed_persona_id", "persona_id_present")
    apply_nonneg_int_fields(metrics, payload, _INT_FIELDS)
    apply_load_error_present(metrics, payload)
    apply_optional_int_field(
        metrics,
        payload,
        "workflow_yaml_top_level_version_int",
        "workflow_yaml_version_int",
    )
    return metrics


def agent_evaluator_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    rows = metrics_table_rows(metrics, _TABLE_ROWS)
    if isinstance(metrics, Mapping) and metrics.get("load_error_present") is True:
        rows.append({"field": "Load error", "value": "yes"})
    return rows


def agent_evaluator_workflow_explainer_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    parts: list[str] = []
    if metrics.get("would_emit_stage_started") is True:
        parts.append("stage **would emit**")
    elif metrics.get("env_forces_off") is True:
        parts.append("env **forces off**")
    elif metrics.get("env_forces_on") is True:
        parts.append("env **forces on**")
    if metrics.get("yaml_parsed_enabled") is True:
        parts.append("YAML enabled")
    if metrics.get("llm_evaluation_enabled") is True:
        parts.append("LLM evaluation **on**")
    if metrics.get("would_emit_llm_evaluation") is True:
        parts.append("LLM branch **would emit**")
    if metrics.get("auto_promote_disabled") is True:
        parts.append("auto-promote **disabled** (env)")
    if metrics.get("auto_create_disabled") is True:
        parts.append("auto-create **disabled** (env)")
    true_b = metrics.get("yaml_true_bool_value_count", 0)
    if isinstance(true_b, int) and not isinstance(true_b, bool) and true_b > 0:
        parts.append(f"**{true_b}** YAML ``true`` bool(s)")
    if metrics.get("load_error_present") is True:
        parts.append("load error")
    return metrics_caption("Agent evaluator explainer metrics: ", parts)


(
    agent_evaluator_workflow_explainer_operator_metrics_export_json,
    agent_evaluator_workflow_explainer_operator_metrics_table_rows_csv,
    agent_evaluator_workflow_explainer_operator_metrics_export_filename_slug,
) = bind_operator_metrics_exports(
    export_slug="agent_evaluator_workflow_explainer_operator_metrics",
)
