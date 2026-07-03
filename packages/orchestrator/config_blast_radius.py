from __future__ import annotations

from typing import Any


def _effective_flags(meta: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    uc = meta.get("universal_critique_effective")
    if isinstance(uc, dict):
        out["universal_critique"] = {
            k: uc.get(k)
            for k in (
                "default_enabled",
                "unanimous_gate_enforce",
                "impl_llm",
                "tw_enabled",
            )
        }
    ae = meta.get("agent_evaluator_effective")
    if isinstance(ae, dict):
        out["agent_evaluator"] = {"enabled": ae.get("enabled")}
    ms = meta.get("micro_slice_effective")
    if isinstance(ms, dict) and ms.get("enabled"):
        out["micro_slice"] = {
            "max_files": ms.get("max_files"),
            "max_loc": ms.get("max_loc"),
            "replan_max": ms.get("replan_max"),
        }
    return out


def preview_workflow_blast_radius(
    *,
    repo_root: Any,
    store: Any,
    workflow_profile: str,
    run_limit: int = 50,
    config_materializer: Any | None = None,
) -> dict[str, Any]:
    from pathlib import Path

    from maker.workspace import run_created_metadata_from_rows
    from orchestrator.slice_budget_presets import resolve_slice_budget_preset
    from orchestrator.workflow_registry import (
        effective_universal_critique,
        parse_agent_evaluator_workflow_block,
        parse_micro_slice_workflow_block,
    )

    root = Path(repo_root)
    uc_now = effective_universal_critique(
        root, workflow_profile, config_materializer=config_materializer
    )
    ms_block = parse_micro_slice_workflow_block(
        root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    preset = resolve_slice_budget_preset()
    proposed: dict[str, Any] = {
        "universal_critique": {
            "default_enabled": uc_now.default_enabled,
            "unanimous_gate_enforce": uc_now.unanimous_gate_enforce,
            "impl_llm": uc_now.impl_llm,
            "tw_enabled": uc_now.tw_enabled,
        },
    }
    ae_block = parse_agent_evaluator_workflow_block(
        root,
        workflow_profile,
        config_materializer=config_materializer,
    )
    proposed["agent_evaluator"] = {"enabled": ae_block.enabled}
    if ms_block.enabled:
        proposed["micro_slice"] = {
            "max_files": preset.max_files,
            "max_loc": preset.max_loc,
            "replan_max": preset.replan_max,
        }

    affected: list[dict[str, Any]] = []
    for run_id in store.list_recent_run_ids(limit=run_limit, workflow_profile=workflow_profile):
        rows = store.list_run_events(str(run_id))
        meta = run_created_metadata_from_rows(rows)
        if not meta:
            continue
        frozen = _effective_flags(meta)
        if frozen == proposed:
            continue
        wf = (rows[0].get("payload") or {}).get("workflow_profile") if rows else None
        if isinstance(rows[0].get("payload"), dict):
            wf = rows[0]["payload"].get("workflow_profile")
        if wf and str(wf) != workflow_profile:
            continue
        affected.append(
            {
                "run_id": str(run_id),
                "frozen_effective": frozen,
                "proposed_effective": proposed,
            },
        )
    return {
        "workflow_profile": workflow_profile,
        "proposed_effective": proposed,
        "affected_run_count": len(affected),
        "affected_runs": affected[:25],
    }
