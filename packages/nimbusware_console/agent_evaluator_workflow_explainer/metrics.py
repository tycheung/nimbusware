from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
)


def agent_evaluator_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
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
    if not isinstance(payload, Mapping):
        return metrics
    metrics["yaml_key_present"] = payload.get("agent_evaluator_yaml_key_present") is True
    metrics["yaml_parsed_enabled"] = payload.get("yaml_parsed_enabled") is True
    metrics["llm_evaluation_enabled"] = payload.get("yaml_parsed_llm_evaluation_enabled") is True
    metrics["would_emit_stage_started"] = payload.get("would_emit_stage_started") is True
    metrics["would_emit_llm_evaluation"] = payload.get("would_emit_llm_evaluation") is True
    env = payload.get("HERMES_AGENT_EVALUATOR")
    if isinstance(env, dict):
        metrics["env_forces_on"] = env.get("forces_on") is True
        metrics["env_forces_off"] = env.get("forces_off") is True
        metrics["env_unset"] = env.get("unset") is True
    ap = payload.get("HERMES_AGENT_EVALUATOR_AUTO_PROMOTE")
    if isinstance(ap, dict):
        metrics["auto_promote_disabled"] = ap.get("disables_auto_promote") is True
    ac = payload.get("HERMES_AGENT_EVALUATOR_AUTO_CREATE")
    if isinstance(ac, dict):
        metrics["auto_create_disabled"] = ac.get("disables_auto_create") is True
    pid = payload.get("yaml_parsed_persona_id")
    metrics["persona_id_present"] = isinstance(pid, str) and bool(pid.strip())
    for key, out_key in (
        ("agent_evaluator_yaml_true_bool_value_count", "yaml_true_bool_value_count"),
        ("agent_evaluator_yaml_false_bool_value_count", "yaml_false_bool_value_count"),
    ):
        raw = payload.get(key)
        if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0:
            metrics[out_key] = raw
    err = payload.get("load_error")
    metrics["load_error_present"] = isinstance(err, str) and bool(err.strip())
    ver = payload.get("workflow_yaml_top_level_version_int")
    if isinstance(ver, int) and not isinstance(ver, bool):
        metrics["workflow_yaml_version_int"] = ver
    return metrics


def agent_evaluator_workflow_explainer_operator_metrics_table_rows(
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
            "field": "YAML parsed enabled",
            "value": str(metrics.get("yaml_parsed_enabled", False)).lower(),
        },
        {
            "field": "Would emit stage",
            "value": str(metrics.get("would_emit_stage_started", False)).lower(),
        },
        {
            "field": "Env forces on",
            "value": str(metrics.get("env_forces_on", False)).lower(),
        },
        {
            "field": "Env forces off",
            "value": str(metrics.get("env_forces_off", False)).lower(),
        },
        {
            "field": "Env unset",
            "value": str(metrics.get("env_unset", True)).lower(),
        },
        {
            "field": "Persona id present",
            "value": str(metrics.get("persona_id_present", False)).lower(),
        },
        {
            "field": "LLM evaluation enabled",
            "value": str(metrics.get("llm_evaluation_enabled", False)).lower(),
        },
        {
            "field": "Would emit LLM branch",
            "value": str(metrics.get("would_emit_llm_evaluation", False)).lower(),
        },
        {
            "field": "Auto-promote disabled (env)",
            "value": str(metrics.get("auto_promote_disabled", False)).lower(),
        },
        {
            "field": "Auto-create disabled (env)",
            "value": str(metrics.get("auto_create_disabled", False)).lower(),
        },
        {
            "field": "YAML true bool count",
            "value": str(metrics.get("yaml_true_bool_value_count", 0)),
        },
        {
            "field": "YAML false bool count",
            "value": str(metrics.get("yaml_false_bool_value_count", 0)),
        },
    ]
    ver = metrics.get("workflow_yaml_version_int")
    if isinstance(ver, int) and not isinstance(ver, bool):
        rows.append({"field": "Workflow YAML version", "value": str(ver)})
    if metrics.get("load_error_present") is True:
        rows.append({"field": "Load error", "value": "yes"})
    return rows


def agent_evaluator_workflow_explainer_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(metrics)


def agent_evaluator_workflow_explainer_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


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
    if not parts:
        return None
    return "Agent evaluator explainer metrics: " + ", ".join(parts) + "."


def agent_evaluator_workflow_explainer_operator_metrics_export_filename_slug() -> str:
    return "agent_evaluator_workflow_explainer_operator_metrics"
