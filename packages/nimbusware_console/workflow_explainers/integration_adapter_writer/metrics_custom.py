from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nimbusware_console.explainer_core.metrics_scaffold import (
    metrics_table_rows,
    normalize_metrics_table_rows,
)

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

_IAW_BOOL_AS_YES = frozenset(
    {
        "YAML key present",
        "Workflow enabled",
        "Effective enabled",
        "Would emit stage",
        "Live path active",
    }
)


def integration_adapter_writer_post_process(
    metrics: dict[str, Any],
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
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


def integration_adapter_writer_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows = metrics_table_rows(metrics, _IAW_TABLE_ROWS)
    if metrics.get("yaml_key_present") is True and not any(
        r["field"] == "YAML key present" for r in rows
    ):
        rows.insert(0, {"field": "YAML key present", "value": "yes"})
    return normalize_metrics_table_rows(
        rows,
        bool_as_yes=_IAW_BOOL_AS_YES,
        present_as={"Workflow YAML path": "present"},
    )


def integration_adapter_writer_caption(metrics: Mapping[str, Any] | None) -> str | None:
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
