from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.integration_adapter_writer_stage import (
    integration_adapter_writer_stage_would_emit,
)
from nimbusware_orchestrator.workflow_integration_adapter_writer import (
    integration_adapter_writer_effective,
    parse_integration_adapter_writer_workflow_block,
)
from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict, workflow_profile_path
from nimbusware_console.config_materializer import console_config_materializer


def _relative_under(repo_root: Path, path: Path) -> str:
    root = repo_root.resolve()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path.resolve())


def _json_safe_yaml_fragment(raw: object) -> object:
    if raw is None or isinstance(raw, (bool, int, float, str)):
        return raw
    if isinstance(raw, dict):
        return {str(k): _json_safe_yaml_fragment(v) for k, v in raw.items()}
    if isinstance(raw, list):
        return [_json_safe_yaml_fragment(x) for x in raw]
    return str(raw)


def _nimbusware_integration_adapter_writer_env_summary() -> dict[str, Any]:
    raw = os.environ.get("NIMBUSWARE_INTEGRATION_ADAPTER_WRITER", "")
    low = raw.strip().lower()
    if not low:
        return {"raw": raw, "forces_off": False, "forces_on": False, "unset": True}
    if low in ("0", "false", "no"):
        return {"raw": raw, "forces_off": True, "forces_on": False, "unset": False}
    if low in ("1", "true", "yes"):
        return {"raw": raw, "forces_off": False, "forces_on": True, "unset": False}
    return {
        "raw": raw,
        "forces_off": False,
        "forces_on": False,
        "unset": True,
        "unrecognised_value": True,
    }


def integration_adapter_writer_env_gate_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    env = payload.get("NIMBUSWARE_INTEGRATION_ADAPTER_WRITER")
    if not isinstance(env, Mapping):
        return None
    if env.get("forces_off"):
        return (
            "Integration Adapter Writer env: **NIMBUSWARE_INTEGRATION_ADAPTER_WRITER** "
            "kill-switch active — workflow enable ignored."
        )
    if env.get("forces_on"):
        return (
            "Integration Adapter Writer env: **NIMBUSWARE_INTEGRATION_ADAPTER_WRITER** "
            "force-on — scaffold may activate when pipeline wiring lands."
        )
    if env.get("unset"):
        return (
            "Integration Adapter Writer env: unset — "
            "workflow ``integration_adapter_writer.enabled`` controls scaffold."
        )
    return None


def integration_adapter_writer_fleet_manifest_count(repo_root: Path) -> int:
    manifest_dir = repo_root / ".nimbusware" / "integration_adapter_writer"
    if not manifest_dir.is_dir():
        return 0
    return sum(1 for path in manifest_dir.rglob("manifest.json") if path.is_file())


def integration_adapter_writer_workflow_explainer_payload(
    repo_root: Path,
    workflow_profile: str | None,
) -> dict[str, Any]:
    materializer = console_config_materializer(repo_root)
    block = parse_integration_adapter_writer_workflow_block(
        repo_root,
        workflow_profile,
        config_materializer=materializer,
    )
    effective = integration_adapter_writer_effective(block)
    would_emit = integration_adapter_writer_stage_would_emit(
        repo_root,
        workflow_profile,
        config_materializer=materializer,
    )
    out: dict[str, Any] = {
        "workflow_profile": workflow_profile,
        "NIMBUSWARE_INTEGRATION_ADAPTER_WRITER": _nimbusware_integration_adapter_writer_env_summary(),
        "workflow_block": {
            "enabled": block.enabled,
            "target_adapter_kind": block.target_adapter_kind,
            "stub_only": block.stub_only,
        },
        "effective_enabled": effective,
        "would_emit_stage_started": would_emit,
        "scaffold_status": ("stub_only" if block.stub_only else "live_adapter_recorded"),
        "fleet_workspace_manifest_count": integration_adapter_writer_fleet_manifest_count(
            repo_root,
        ),
    }
    if workflow_profile:
        try:
            path = workflow_profile_path(repo_root, str(workflow_profile).strip())
            out["workflow_yaml_path"] = _relative_under(repo_root, path)
            raw = workflow_profile_dict(
                repo_root,
                str(workflow_profile).strip(),
                materializer=materializer,
            )
            sub = raw.get("integration_adapter_writer")
            if sub is not None:
                out["workflow_yaml_fragment"] = _json_safe_yaml_fragment(sub)
        except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError) as exc:
            out["load_error"] = str(exc)
    return out


def integration_adapter_writer_explainer_export_json(
    payload: Mapping[str, Any] | None,
) -> str:
    if not isinstance(payload, Mapping):
        return "{}"
    return json.dumps(dict(payload), indent=2, ensure_ascii=False)


def integration_adapter_writer_workflow_explainer_operator_metrics(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
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
    if (
        isinstance(payload.get("workflow_yaml_path"), str)
        and str(
            payload.get("workflow_yaml_path"),
        ).strip()
    ):
        metrics["workflow_yaml_path_present"] = True
    fcount = payload.get("fleet_workspace_manifest_count")
    if isinstance(fcount, int) and fcount >= 0:
        metrics["fleet_manifest_count"] = fcount
    return metrics


def integration_adapter_writer_workflow_explainer_operator_metrics_table_rows(
    metrics: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(metrics, Mapping):
        return []
    rows: list[dict[str, str]] = []
    if metrics.get("yaml_key_present") is True:
        rows.append({"field": "YAML key present", "value": "yes"})
    if metrics.get("workflow_enabled") is True:
        rows.append({"field": "Workflow enabled", "value": "yes"})
    if metrics.get("effective_enabled") is True:
        rows.append({"field": "Effective enabled", "value": "yes"})
    if metrics.get("would_emit_stage_started") is True:
        rows.append({"field": "Would emit stage", "value": "yes"})
    if metrics.get("live_path_active") is True:
        rows.append({"field": "Live path active", "value": "yes"})
    status = metrics.get("scaffold_status")
    if isinstance(status, str) and status.strip():
        rows.append({"field": "Scaffold status", "value": status.strip()})
    if metrics.get("workflow_yaml_path_present") is True:
        rows.append({"field": "Workflow YAML path", "value": "present"})
    stub = metrics.get("stub_only")
    if isinstance(stub, bool):
        rows.append({"field": "Stub only", "value": str(stub)})
    kind = metrics.get("target_adapter_kind")
    if isinstance(kind, str) and kind.strip():
        rows.append({"field": "Target adapter kind", "value": kind.strip()})
    return rows


def integration_adapter_writer_effective_caption(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    if payload.get("effective_enabled") is True:
        block = payload.get("workflow_block")
        kind = ""
        if isinstance(block, Mapping):
            raw_kind = block.get("target_adapter_kind")
            if isinstance(raw_kind, str) and raw_kind.strip():
                kind = f" ({raw_kind.strip()})"
        return f"Integration Adapter Writer: **effective on**{kind}."
    return "Integration Adapter Writer: **off** (env or workflow gate)."


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


def integration_adapter_writer_from_events(
    rows: list[Mapping[str, Any]],
) -> dict[str, Any] | None:
    """Latest IAW metadata from ``stage.started`` rows."""
    from nimbusware_orchestrator.integration_adapter_writer_stage import (
        INTEGRATION_ADAPTER_WRITER_STAGE,
    )

    for row in reversed(rows):
        if row.get("event_type") != "stage.started":
            continue
        payload = row.get("payload") or {}
        if (payload.get("stage_name") or "") != INTEGRATION_ADAPTER_WRITER_STAGE:
            continue
        meta = row.get("metadata") or {}
        iaw = meta.get("integration_adapter_writer")
        if isinstance(iaw, Mapping):
            return dict(iaw)
    return None


def integration_adapter_writer_run_table_rows(
    iaw: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    if not isinstance(iaw, Mapping):
        return []
    rows: list[dict[str, str]] = []
    for key, label in (
        ("scaffold_status", "Scaffold status"),
        ("target_integration_status", "Target integration"),
        ("target_adapter_kind", "Adapter kind"),
        ("workspace_manifest_path", "Manifest path"),
        ("adapter_module_path", "Adapter module"),
        ("rollback_reason", "Rollback reason"),
    ):
        val = iaw.get(key)
        if val is None or val == "":
            continue
        rows.append({"field": label, "value": str(val)})
    return rows


def integration_adapter_writer_run_caption(iaw: Mapping[str, Any] | None) -> str:
    if not isinstance(iaw, Mapping):
        return "No Integration Adapter Writer stage for this run."
    status = str(iaw.get("target_integration_status") or iaw.get("scaffold_status") or "unknown")
    kind = str(iaw.get("target_adapter_kind") or "").strip()
    prefix = f"{kind}: " if kind else ""
    return f"{prefix}Integration Adapter Writer — {status}."
