from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from agent_core.coercion import is_number, is_strict_int
from nimbusware_console.explainer_core.explainer_caption_parts import (
    agent_evaluator_caption_parts,
    escalation_suppress_caption_parts,
    security_scan_metadata_caption_parts,
    self_refinement_caption_parts,
    universal_critique_caption_parts,
)
from nimbusware_console.explainer_core.metrics_scaffold import metrics_table_rows
from nimbusware_console.explainer_core.operator_metrics_exports import (
    caption_from_parts,
    install_operator_metrics_module,
)
from nimbusware_console.explainer_core.schema_metrics import build_operator_metrics
from nimbusware_console.explainer_core.workflow_metrics_spec import (
    install_workflow_metrics_from_spec,
    repo_explainer_spec,
)

CaptionPartsFn = Callable[[Mapping[str, Any]], list[str]]
CustomInstallFn = Callable[[dict[str, object]], None]

_IAW_METRIC_DEFAULTS: dict[str, Any] = {
    "yaml_key_present": False,
    "workflow_enabled": False,
    "effective_enabled": False,
    "would_emit_stage_started": False,
    "live_path_active": False,
    "scaffold_status": None,
    "workflow_yaml_path_present": False,
    "fleet_manifest_count": 0,
    "stub_only": None,
    "target_adapter_kind": None,
}

_IAW_TABLE_ROWS: tuple[tuple[str, str], ...] = (
    ("YAML key present", "yaml_key_present"),
    ("Workflow enabled", "workflow_enabled"),
    ("Effective enabled", "effective_enabled"),
    ("Would emit stage", "would_emit_stage_started"),
    ("Live path active", "live_path_active"),
    ("Scaffold status", "scaffold_status"),
    ("Workflow YAML path", "workflow_yaml_path_present"),
    ("Stub only", "stub_only"),
    ("Target adapter kind", "target_adapter_kind"),
)


def _integration_adapter_writer_metrics(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    metrics = build_operator_metrics(
        payload,
        _IAW_METRIC_DEFAULTS,
        nested_bool_fields=(("workflow_block", (("enabled", "workflow_enabled"),)),),
        bool_fields=(
            ("effective_enabled", "effective_enabled"),
            ("would_emit_stage_started", "would_emit_stage_started"),
        ),
        str_present=(("workflow_yaml_path", "workflow_yaml_path_present"),),
        int_fields=(("fleet_workspace_manifest_count", "fleet_manifest_count"),),
    )
    if not isinstance(payload, Mapping):
        return metrics
    block = payload.get("workflow_block")
    if isinstance(block, Mapping):
        metrics["yaml_key_present"] = True
        stub = block.get("stub_only")
        if isinstance(stub, bool):
            metrics["stub_only"] = stub
            if stub is False:
                metrics["live_path_active"] = True
        kind = block.get("target_adapter_kind")
        if isinstance(kind, str) and kind.strip():
            metrics["target_adapter_kind"] = kind.strip()
    status = payload.get("scaffold_status")
    if isinstance(status, str) and status.strip():
        metrics["scaffold_status"] = status.strip()
    return metrics


def _integration_adapter_writer_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows = metrics_table_rows(metrics, _IAW_TABLE_ROWS)
    if metrics.get("yaml_key_present") is True and not any(
        r["field"] == "YAML key present" for r in rows
    ):
        rows.insert(0, {"field": "YAML key present", "value": "yes"})
    for row in rows:
        if row["field"] == "YAML key present" and row["value"] == "true":
            row["value"] = "yes"
        if row["field"] in (
            "Workflow enabled",
            "Effective enabled",
            "Would emit stage",
            "Live path active",
        ):
            if row["value"] == "true":
                row["value"] = "yes"
        if row["field"] == "Workflow YAML path" and row["value"] == "true":
            row["value"] = "present"
    return rows


def _integration_adapter_writer_caption(metrics: Mapping[str, Any] | None) -> str | None:
    if not isinstance(metrics, Mapping):
        return None
    if metrics.get("effective_enabled") is True:
        kind = metrics.get("target_adapter_kind")
        stub = metrics.get("stub_only")
        live = metrics.get("live_path_active") is True
        if stub is True:
            stub_txt = "stub-only"
        elif live:
            stub_txt = "live path (metadata recorded)"
        else:
            stub_txt = "live path deferred"
        kind_txt = f" ({kind})" if isinstance(kind, str) and kind.strip() else ""
        if metrics.get("would_emit_stage_started") is True:
            emit_hint = (
                "; pipeline **would emit** live ``stage.started``"
                if live
                else "; pipeline **would emit** stub ``stage.started``"
            )
        else:
            emit_hint = ""
        return (
            f"Integration Adapter Writer scaffold: **enabled**{kind_txt} — {stub_txt}{emit_hint}."
        )
    if metrics.get("yaml_key_present") is True:
        return "Integration Adapter Writer scaffold: YAML present but **disabled**."
    return None


def _install_integration_adapter_writer_metrics(namespace: dict[str, object]) -> None:
    install_operator_metrics_module(
        namespace,
        module_prefix="integration_adapter_writer_workflow_explainer",
        metrics=_integration_adapter_writer_metrics,
        table_rows=_integration_adapter_writer_table_rows,
        caption=_integration_adapter_writer_caption,
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


def _integrator_threshold_metrics(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    from nimbusware_console.workflow_explainers.integrator_threshold.keys import (
        get_preview_effective_min_score,
    )

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


def _integrator_threshold_table_rows(metrics: Mapping[str, Any] | None) -> list[dict[str, str]]:
    return metrics_table_rows(
        metrics,
        _INTEGRATOR_TABLE_ROWS,
        include_when=lambda m, key: (
            key not in {"min_score_pipeline", "min_score_preview", "load_error_present"}
            or (key == "load_error_present" and m.get("load_error_present") is True)
            or m.get(key) is not None
        ),
    )


def _integrator_threshold_caption_parts(metrics: Mapping[str, Any]) -> list[str]:
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


def _install_integrator_threshold_metrics(namespace: dict[str, object]) -> None:
    install_operator_metrics_module(
        namespace,
        module_prefix="integrator_threshold_explainer",
        metrics=_integrator_threshold_metrics,
        table_rows=_integrator_threshold_table_rows,
        caption=caption_from_parts(
            "Integrator threshold explainer metrics: ",
            _integrator_threshold_caption_parts,
        ),
    )


_YAML_EXPLAINERS: dict[str, CaptionPartsFn] = {
    "agent_evaluator": agent_evaluator_caption_parts,
    "escalation_suppress": escalation_suppress_caption_parts,
    "universal_critique": universal_critique_caption_parts,
    "security_scan_metadata": security_scan_metadata_caption_parts,
    "self_refinement": self_refinement_caption_parts,
}

_CUSTOM_INSTALL: dict[str, CustomInstallFn] = {
    "integration_adapter_writer": _install_integration_adapter_writer_metrics,
    "integrator_threshold": _install_integrator_threshold_metrics,
}


def install_explainer_metrics(slug: str, namespace: dict[str, object]) -> None:
    custom = _CUSTOM_INSTALL.get(slug)
    if custom is not None:
        custom(namespace)
        return
    caption_parts = _YAML_EXPLAINERS.get(slug)
    if caption_parts is None:
        msg = f"unknown workflow explainer slug: {slug!r}"
        raise KeyError(msg)
    install_workflow_metrics_from_spec(
        namespace,
        repo_explainer_spec(slug),
        caption_parts_fn=caption_parts,
    )
