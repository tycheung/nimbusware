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

_PREFIX = "agent_evaluator_workflow_explainer"

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


def _caption_parts(metrics: Mapping[str, Any]) -> list[str]:
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
    if is_strict_int(true_b) and true_b > 0:
        parts.append(f"**{true_b}** YAML ``true`` bool(s)")
    if metrics.get("load_error_present") is True:
        parts.append("load error")
    return parts


(
    agent_evaluator_workflow_explainer_operator_metrics,
    agent_evaluator_workflow_explainer_operator_metrics_table_rows,
    agent_evaluator_workflow_explainer_operator_metrics_caption,
    agent_evaluator_workflow_explainer_operator_metrics_export_json,
    agent_evaluator_workflow_explainer_operator_metrics_table_rows_csv,
    agent_evaluator_workflow_explainer_operator_metrics_export_filename_slug,
) = install_operator_metrics_module(
    globals(),
    module_prefix=_PREFIX,
    metrics=build_metrics_fn(
        _DEFAULTS,
        bool_fields=(
            ("agent_evaluator_yaml_key_present", "yaml_key_present"),
            ("yaml_parsed_enabled", "yaml_parsed_enabled"),
            ("yaml_parsed_llm_evaluation_enabled", "llm_evaluation_enabled"),
            ("would_emit_stage_started", "would_emit_stage_started"),
            ("would_emit_llm_evaluation", "would_emit_llm_evaluation"),
        ),
        int_fields=(
            ("agent_evaluator_yaml_true_bool_value_count", "yaml_true_bool_value_count"),
            ("agent_evaluator_yaml_false_bool_value_count", "yaml_false_bool_value_count"),
        ),
        env_tri_state=("NIMBUSWARE_AGENT_EVALUATOR",),
        env_flags=(
            (
                "NIMBUSWARE_AGENT_EVALUATOR_AUTO_PROMOTE",
                "disables_auto_promote",
                "auto_promote_disabled",
            ),
            (
                "NIMBUSWARE_AGENT_EVALUATOR_AUTO_CREATE",
                "disables_auto_create",
                "auto_create_disabled",
            ),
        ),
        str_present=(("yaml_parsed_persona_id", "persona_id_present"),),
        optional_int=(("workflow_yaml_top_level_version_int", "workflow_yaml_version_int"),),
        load_error=True,
    ),
    table_rows=table_rows_fn(_TABLE_ROWS, append_load_error_row=True),
    caption=caption_from_parts("Agent evaluator explainer metrics: ", _caption_parts),
)
