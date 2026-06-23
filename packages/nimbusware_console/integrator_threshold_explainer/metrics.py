from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.metrics_scaffold import (
    apply_bool_payload_fields,
    apply_nonneg_int_fields,
    default_operator_metrics,
    metrics_caption,
    metrics_table_rows,
)
from nimbusware_console.explainer_core.operator_metrics_exports import (
    install_named_operator_metrics_exports,
)
from nimbusware_console.integrator_threshold_explainer.keys import (
    get_preview_effective_min_score,
)

_DEFAULTS: dict[str, Any] = {
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

_TABLE_ROWS: tuple[tuple[str, str], ...] = (
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


def integrator_threshold_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics = default_operator_metrics(_DEFAULTS)
    if not isinstance(payload, Mapping):
        return metrics
    emission = payload.get("gate_event_emission")
    if isinstance(emission, Mapping):
        apply_bool_payload_fields(
            metrics,
            emission,
            (
                ("would_emit_integrator_gate_event", "would_emit_gate_event"),
                ("thresholds_yaml_exists", "thresholds_yaml_exists"),
                ("forces_on", "env_forces_on"),
                ("forces_off", "env_forces_off"),
            ),
        )
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
        apply_nonneg_int_fields(
            metrics,
            wf_gate,
            (("project_tags_list_length", "project_tags_list_length"),),
        )
    paste_errs = payload.get("paste_parse_errors")
    if isinstance(paste_errs, list) and paste_errs:
        metrics["load_error_present"] = True
    return metrics


def integrator_threshold_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    return metrics_table_rows(
        metrics,
        _TABLE_ROWS,
        include_when=lambda m, key: (
            key not in {"min_score_pipeline", "min_score_preview", "load_error_present"}
            or (key == "load_error_present" and m.get("load_error_present") is True)
            or m.get(key) is not None
        ),
    )


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
    return metrics_caption("Integrator threshold explainer metrics: ", parts)


(
    integrator_threshold_explainer_operator_metrics_export_json,
    integrator_threshold_explainer_operator_metrics_table_rows_csv,
    integrator_threshold_explainer_operator_metrics_export_filename_slug,
) = install_named_operator_metrics_exports(
    globals(),
    "integrator_threshold_explainer",
    export_slug="integrator_threshold_explainer_operator_metrics",
)
