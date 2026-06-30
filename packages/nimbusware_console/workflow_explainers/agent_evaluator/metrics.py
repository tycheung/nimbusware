from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_strict_int
from nimbusware_console.explainer_core.workflow_metrics_spec import (
    install_workflow_metrics_from_spec,
    repo_explainer_spec,
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


install_workflow_metrics_from_spec(
    globals(),
    repo_explainer_spec("agent_evaluator"),
    caption_parts_fn=_caption_parts,
)
