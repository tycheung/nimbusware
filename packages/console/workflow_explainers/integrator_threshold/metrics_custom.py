from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_number, is_strict_int
from console.explainer_core.operator_metrics_exports import caption_from_parts
from console.workflow_explainers.integrator_threshold.keys import (
    get_preview_effective_min_score,
)


def integrator_threshold_post_process(
    metrics: dict[str, Any],
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    preview = get_preview_effective_min_score(payload) if isinstance(payload, Mapping) else None
    if is_number(preview):
        metrics["min_score_preview"] = float(preview)
    pipe = metrics.get("min_score_pipeline")
    prev = metrics.get("min_score_preview")
    if pipe is not None and prev is not None:
        metrics["min_scores_agree"] = pipe == prev
    return metrics


def integrator_threshold_caption_parts(metrics: Mapping[str, Any]) -> list[str]:
    parts: list[str] = []
    if metrics.get("would_emit_gate_event") is True:
        parts.append("gate **would emit**")
    elif metrics.get("would_emit_gate_event") is False and (
        metrics.get("thresholds_yaml_exists") is True or metrics.get("env_forces_off") is True
    ):
        parts.append("gate **would not emit**")
    if metrics.get("env_forces_on") is True:
        parts.append("env **forces gate on**")
    elif metrics.get("env_forces_off") is True:
        parts.append("env **forces gate off**")
    if metrics.get("min_scores_agree") is True:
        pipe = metrics.get("min_score_pipeline")
        if is_number(pipe):
            parts.append(f"min score **{float(pipe)}** (pipeline/preview agree)")
    elif metrics.get("min_scores_agree") is False:
        pipe = metrics.get("min_score_pipeline")
        preview = metrics.get("min_score_preview")
        if isinstance(pipe, (int, float)) and isinstance(preview, (int, float)):
            parts.append(f"min score mismatch (pipeline **{pipe}**, preview **{preview}**)")
    tags_len = metrics.get("project_tags_list_length", 0)
    if is_strict_int(tags_len) and tags_len > 0:
        suffix = "tag" if tags_len == 1 else "tags"
        parts.append(f"**{tags_len}** workflow project_{suffix}")
    if metrics.get("load_error_present") is True:
        parts.append("paste parse error(s)")
    return parts


integrator_threshold_caption = caption_from_parts(
    "Integrator threshold explainer metrics: ",
    integrator_threshold_caption_parts,
)
