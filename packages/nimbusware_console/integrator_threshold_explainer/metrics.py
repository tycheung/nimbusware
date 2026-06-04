from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from nimbusware_console.components.operator_metrics import (
    field_value_table_rows_csv,
    mapping_export_json,
)
from nimbusware_console.integrator_threshold_explainer.keys import (
    get_preview_effective_min_score,
)


def integrator_threshold_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
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
    if not isinstance(payload, Mapping):
        return metrics
    emission = payload.get("gate_event_emission")
    if isinstance(emission, Mapping):
        metrics["would_emit_gate_event"] = emission.get("would_emit_integrator_gate_event") is True
        metrics["thresholds_yaml_exists"] = emission.get("thresholds_yaml_exists") is True
        metrics["env_forces_on"] = emission.get("forces_on") is True
        metrics["env_forces_off"] = emission.get("forces_off") is True
    thr = payload.get("thresholds_yaml")
    if isinstance(thr, Mapping) and thr.get("exists") is True:
        metrics["thresholds_yaml_exists"] = True
    pipe = payload.get("pipeline_effective_min_score_to_pass")
    preview = get_preview_effective_min_score(payload)
    if isinstance(pipe, (int, float)) and not isinstance(pipe, bool):
        metrics["min_score_pipeline"] = float(pipe)
    if isinstance(preview, (int, float)) and not isinstance(preview, bool):
        metrics["min_score_preview"] = float(preview)
    if metrics["min_score_pipeline"] is not None and metrics["min_score_preview"] is not None:
        metrics["min_scores_agree"] = metrics["min_score_pipeline"] == metrics["min_score_preview"]
    wf_gate = payload.get("workflow_integrator_gate")
    if isinstance(wf_gate, Mapping):
        raw_len = wf_gate.get("project_tags_list_length")
        if isinstance(raw_len, int) and not isinstance(raw_len, bool) and raw_len >= 0:
            metrics["project_tags_list_length"] = raw_len
    paste_errs = payload.get("paste_parse_errors")
    if isinstance(paste_errs, list) and paste_errs:
        metrics["load_error_present"] = True
    return metrics


def integrator_threshold_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = [
        {
            "field": "Would emit gate event",
            "value": str(metrics.get("would_emit_gate_event", False)).lower(),
        },
        {
            "field": "Thresholds YAML exists",
            "value": str(metrics.get("thresholds_yaml_exists", False)).lower(),
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
            "field": "Min scores agree",
            "value": str(metrics.get("min_scores_agree", False)).lower(),
        },
        {
            "field": "Project tags (workflow)",
            "value": str(metrics.get("project_tags_list_length", 0)),
        },
    ]
    pipe = metrics.get("min_score_pipeline")
    if isinstance(pipe, (int, float)) and not isinstance(pipe, bool):
        rows.append({"field": "Min score pipeline", "value": str(pipe)})
    preview = metrics.get("min_score_preview")
    if isinstance(preview, (int, float)) and not isinstance(preview, bool):
        rows.append({"field": "Min score preview", "value": str(preview)})
    if metrics.get("load_error_present") is True:
        rows.append({"field": "Load error", "value": "yes"})
    return rows


def integrator_threshold_explainer_operator_metrics_export_json(
    metrics: Mapping[str, Any] | None,
) -> str:
    return mapping_export_json(metrics)


def integrator_threshold_explainer_operator_metrics_table_rows_csv(
    rows: Sequence[Mapping[str, str]],
) -> str:
    return field_value_table_rows_csv(rows)


def integrator_threshold_explainer_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
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
        if isinstance(pipe, (int, float)) and not isinstance(pipe, bool):
            parts.append(f"min score **{float(pipe)}** (pipeline/preview agree)")
    elif metrics.get("min_scores_agree") is False:
        pipe = metrics.get("min_score_pipeline")
        preview = metrics.get("min_score_preview")
        if isinstance(pipe, (int, float)) and isinstance(preview, (int, float)):
            parts.append(f"min score mismatch (pipeline **{pipe}**, preview **{preview}**)")
    tags_len = metrics.get("project_tags_list_length", 0)
    if isinstance(tags_len, int) and not isinstance(tags_len, bool) and tags_len > 0:
        suffix = "tag" if tags_len == 1 else "tags"
        parts.append(f"**{tags_len}** workflow project_{suffix}")
    if metrics.get("load_error_present") is True:
        parts.append("paste parse error(s)")
    if not parts:
        return None
    return "Integrator threshold explainer metrics: " + ", ".join(parts) + "."


def integrator_threshold_explainer_operator_metrics_export_filename_slug() -> str:
    return "integrator_threshold_explainer_operator_metrics"
