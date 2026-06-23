from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.metrics_scaffold import (
    apply_str_present,
    default_operator_metrics,
    metrics_table_rows,
)
from nimbusware_console.explainer_core.operator_metrics_exports import (
    install_named_operator_metrics_exports,
)

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


def integration_adapter_writer_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics = default_operator_metrics(_IAW_METRIC_DEFAULTS)
    if not isinstance(payload, Mapping):
        return metrics
    block = payload.get("workflow_block")
    if isinstance(block, Mapping):
        metrics["yaml_key_present"] = True
        if block.get("enabled") is True:
            metrics["workflow_enabled"] = True
        stub = block.get("stub_only")
        if isinstance(stub, bool):
            metrics["stub_only"] = stub
            if stub is False:
                metrics["live_path_active"] = True
        kind = block.get("target_adapter_kind")
        if isinstance(kind, str) and kind.strip():
            metrics["target_adapter_kind"] = kind.strip()
    if payload.get("effective_enabled") is True:
        metrics["effective_enabled"] = True
    if payload.get("would_emit_stage_started") is True:
        metrics["would_emit_stage_started"] = True
    status = payload.get("scaffold_status")
    if isinstance(status, str) and status.strip():
        metrics["scaffold_status"] = status.strip()
    apply_str_present(metrics, payload, "workflow_yaml_path", "workflow_yaml_path_present")
    fcount = payload.get("fleet_workspace_manifest_count")
    if isinstance(fcount, int) and fcount >= 0:
        metrics["fleet_manifest_count"] = fcount
    return metrics


def integration_adapter_writer_workflow_explainer_operator_metrics_table_rows(
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


def integration_adapter_writer_workflow_explainer_operator_metrics_caption(
    metrics: Mapping[str, Any] | None,
) -> str | None:
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


(
    integration_adapter_writer_workflow_explainer_operator_metrics_export_json,
    integration_adapter_writer_workflow_explainer_operator_metrics_table_rows_csv,
    integration_adapter_writer_workflow_explainer_operator_metrics_export_filename_slug,
) = install_named_operator_metrics_exports(
    globals(),
    "integration_adapter_writer_workflow_explainer",
    export_slug="integration_adapter_writer_workflow_explainer_operator_metrics",
)
