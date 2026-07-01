from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agent_core.coercion import is_number, is_strict_int
from nimbusware_console.explainer_core.metrics_scaffold import metrics_table_rows
from nimbusware_console.explainer_core.operator_metrics_exports import caption_from_parts
from nimbusware_console.explainer_core.schema_metrics import build_operator_metrics
from nimbusware_console.workflow_explainers.integrator_threshold.keys import (
    get_preview_effective_min_score,
)

_INTEGRATOR_DEFAULTS: dict[str, Any] = {
    "would_emit_gate_event": False,
    "thresholds_yaml_exists": False,
    "env_forces_on": False,
    "env_forces_off": False,
    "min_score_pipeline": None,
    "min_score_preview": None,
    "min_scores_agree": False,
    "project_tags_list_length": 0,
    "load_error_present": False,
}

_INTEGRATOR_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("Would emit gate event", "would_emit_gate_event"),
    ("Thresholds YAML exists", "thresholds_yaml_exists"),
    ("Env forces on", "env_forces_on"),
    ("Env forces off", "env_forces_off"),
    ("Min scores agree", "min_scores_agree"),
    ("Project tags (workflow)", "project_tags_list_length"),
    ("Min score pipeline", "min_score_pipeline"),
    ("Min score preview", "min_score_preview"),
    ("Load error", "load_error_present"),
)


def integrator_threshold_metrics(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    metrics = build_operator_metrics(
        payload,
        _INTEGRATOR_DEFAULTS,
        nested_bool_fields=(
            (
                "gate_event_emission",
                (
                    ("would_emit_integrator_gate_event", "would_emit_gate_event"),
                    ("thresholds_yaml_exists", "thresholds_yaml_exists"),
                    ("forces_on", "env_forces_on"),
                    ("forces_off", "env_forces_off"),
                ),
            ),
        ),
        nested_exists=(("thresholds_yaml", "thresholds_yaml_exists"),),
        float_fields=(("pipeline_effective_min_score_to_pass", "min_score_pipeline"),),
        nested_int_fields=(
            (
                "workflow_integrator_gate",
                (("project_tags_list_length", "project_tags_list_length"),),
            ),
        ),
        list_nonempty_flags=(("paste_parse_errors", "load_error_present"),),
    )
    preview = get_preview_effective_min_score(payload) if isinstance(payload, Mapping) else None
    if is_number(preview):
        metrics["min_score_preview"] = float(preview)
    pipe = metrics.get("min_score_pipeline")
    prev = metrics.get("min_score_preview")
    if pipe is not None and prev is not None:
        metrics["min_scores_agree"] = pipe == prev
    return metrics


def integrator_threshold_table_rows(metrics: Mapping[str, Any] | None) -> list[dict[str, str]]:
    return metrics_table_rows(
        metrics,
        _INTEGRATOR_TABLE_ROWS,
        include_when=lambda m, key: (
            key not in {"min_score_pipeline", "min_score_preview", "load_error_present"}
            or (key == "load_error_present" and m.get("load_error_present") is True)
            or m.get(key) is not None
        ),
    )


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
