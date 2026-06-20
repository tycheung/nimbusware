from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from nimbusware_compute.work_unit import WorkUnitRecord
from nimbusware_orchestrator.mesh_pipeline_hook import CRITIC_STAGE_NAMES
from nimbusware_orchestrator.role_execute import _SUPPORTED_PRODUCERS, dispatch_role_execute

_WRITER_STAGE_TAXONOMY: dict[str, str] = {
    "implementation": "backend_writer",
    "test_writer": "test_writer",
    "frontend_writer": "frontend_writer",
    "plan": "planner",
}

_WRITER_MESH_STAGES = frozenset(_WRITER_STAGE_TAXONOMY)

_CRITIC_EMITTERS: dict[str, str] = {
    "security_critique": "_emit_security_critique_optional",
    "performance_critique": "_emit_performance_critique_optional",
    "network_resilience_critique": "_emit_network_resilience_critique_optional",
}


def _resolve_workspace(payload: dict[str, Any]) -> Path | None:
    raw = payload.get("workspace")
    if raw is None:
        from nimbusware_env.env_flags import env_truthy

        if not env_truthy("NIMBUSWARE_MESH_WORKSPACE_FALLBACK"):
            return None
        from nimbusware_env.env_flags import nimbusware_repo_root_path, nimbusware_workspace_path

        for candidate in (
            nimbusware_workspace_path(default=""),
            nimbusware_repo_root_path(),
        ):
            if candidate.is_dir():
                return candidate
        return None
    path = Path(str(raw)).resolve()
    return path if path.is_dir() else None


def _mesh_orchestrator(workspace: Path) -> Any:
    from nimbusware_orchestrator.runtime_bootstrap import build_runtime_orchestrator

    return build_runtime_orchestrator(
        repo_root=workspace,
        use_materializer_registry=True,
    ).orchestrator


def _run_context(
    orch: Any,
    run_id: UUID,
    payload: dict[str, Any],
) -> tuple[str | None, dict[str, Any] | None]:
    workflow_profile = payload.get("workflow_profile")
    sg_snapshot: dict[str, Any] | None = None
    if isinstance(workflow_profile, str) and workflow_profile.strip():
        wf = workflow_profile.strip()
    else:
        wf = None
    rows = orch._store.list_run_events(str(run_id))
    for row in rows:
        if row.get("event_type") != "run.created":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            break
        if wf is None:
            raw_wf = meta.get("workflow_profile")
            if isinstance(raw_wf, str) and raw_wf.strip():
                wf = raw_wf.strip()
        raw_sg = meta.get("stage_graph_snapshot")
        if isinstance(raw_sg, dict):
            sg_snapshot = raw_sg
        break
    return wf, sg_snapshot


def _execute_campaign_slice(
    orch: Any,
    run_id: UUID,
    slice_id: str,
    *,
    workspace: Path,
) -> dict[str, Any]:
    from agent_core.read.campaign import backlog_from_events
    from nimbusware_orchestrator.micro_slice import parse_slice_plan
    from nimbusware_orchestrator.micro_slice_executor import execute_single_micro_slice

    rows = orch._store.list_run_events(str(run_id))
    backlog = backlog_from_events(rows)
    if backlog is None:
        return {"stage_name": f"campaign.slice:{slice_id}", "error": "no_campaign_backlog"}

    target = None
    for epic in backlog.epics:
        for feature in epic.features:
            for sl in feature.slices:
                if sl.slice_id == slice_id:
                    target = sl
                    break
            if target is not None:
                break
        if target is not None:
            break
    if target is None:
        return {"stage_name": f"campaign.slice:{slice_id}", "error": f"slice_not_found:{slice_id}"}

    plan = parse_slice_plan(
        {
            "slice_id": slice_id,
            "rationale": target.rationale,
            "target_paths": list(target.target_paths),
            "acceptance_criteria": "Campaign backlog slice (mesh worker)",
        },
    )
    completed = backlog.metadata.slices_completed
    gate = execute_single_micro_slice(
        orch,
        run_id,
        slice_index=completed + 1,
        workspace=workspace,
        plan=plan,
        backlog_slice_id=slice_id,
    )
    return {
        "stage_name": f"campaign.slice:{slice_id}",
        "slice_passed": gate.passed,
        "status": "executed",
    }


def _execute_critic_stage(
    orch: Any,
    run_id: UUID,
    stage_name: str,
    *,
    workspace: Path,
    workflow_profile: str | None,
    sg_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    method_name = _CRITIC_EMITTERS.get(stage_name)
    if method_name is None:
        msg = f"unsupported critic stage: {stage_name}"
        raise ValueError(msg)
    emitter = getattr(orch, method_name)
    gate_fail = emitter(
        run_id,
        workspace=workspace,
        workflow_profile=workflow_profile,
        sg_snapshot=sg_snapshot,
    )
    return {
        "stage_name": stage_name,
        "status": "executed",
        "gate_fail": bool(gate_fail),
    }


def _taxonomy_for_stage(rec: WorkUnitRecord, payload: dict[str, Any]) -> str | None:
    raw = payload.get("taxonomy_key") or rec.agent_role or rec.stage_name
    key = str(raw).strip().lower()
    mapped = _WRITER_STAGE_TAXONOMY.get(key, key)
    if mapped in _SUPPORTED_PRODUCERS:
        return mapped
    return None


def _execute_writer_mesh_stage(
    orch: Any,
    run_id: UUID,
    stage_name: str,
    *,
    workspace: Path,
    workflow_profile: str | None,
    sg_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    from nimbusware_orchestrator.workflow_parallel_writers import (
        test_writer_llm_body_enabled,
        test_writer_llm_stub_fallback,
        test_writer_stage_enabled,
    )

    wf = workflow_profile or "default"
    if stage_name == "implementation":
        result = orch._parallel_run_implementation(run_id, sg_snapshot, workspace)
    elif stage_name == "test_writer":
        result = orch._parallel_run_test_writer(
            run_id,
            sg_snapshot,
            workspace,
            real_enabled=test_writer_stage_enabled(orch.repo_root, wf),
            llm_body_enabled=test_writer_llm_body_enabled(orch.repo_root, wf),
            llm_stub_fallback_enabled=test_writer_llm_stub_fallback(orch.repo_root, wf),
            llm_model_id=None,
            llm_base_url=str(
                (orch._base_cfg().get("runtime") or {}).get("base_url", "http://localhost:11434")
            ),
            llm_timeout_seconds=float(
                (orch._base_cfg().get("runtime") or {}).get("request_timeout_seconds", 120),
            ),
        )
    elif stage_name == "frontend_writer":
        result = orch._parallel_run_frontend_writer(run_id, sg_snapshot, workspace)
    else:
        msg = f"unsupported writer mesh stage: {stage_name}"
        raise ValueError(msg)
    return {
        "stage_name": stage_name,
        "status": "executed",
        "executed": True,
        "verifier_exit_code": int(result.verifier_exit_code),
        "verifier_log": str(result.verifier_log),
    }


def execute_mesh_stage(
    orch: Any,
    rec: WorkUnitRecord,
    *,
    workspace: Path,
) -> dict[str, Any]:
    payload = rec.payload or {}
    run_id = rec.run_id
    stage_name = rec.stage_name
    workflow_profile, sg_snapshot = _run_context(orch, run_id, payload)

    if stage_name.startswith("campaign.slice:"):
        slice_id = stage_name.split(":", 1)[1]
        return _execute_campaign_slice(orch, run_id, slice_id, workspace=workspace)

    if stage_name in CRITIC_STAGE_NAMES:
        return _execute_critic_stage(
            orch,
            run_id,
            stage_name,
            workspace=workspace,
            workflow_profile=workflow_profile,
            sg_snapshot=sg_snapshot,
        )

    if stage_name in _WRITER_MESH_STAGES:
        return _execute_writer_mesh_stage(
            orch,
            run_id,
            stage_name,
            workspace=workspace,
            workflow_profile=workflow_profile,
            sg_snapshot=sg_snapshot,
        )

    taxonomy = _taxonomy_for_stage(rec, payload)
    if taxonomy is not None:
        result = dispatch_role_execute(
            orch,
            run_id,
            taxonomy,
            workspace=workspace,
        )
        return dict(result)

    return {
        "status": "skipped",
        "stage_name": stage_name,
        "reason": f"unsupported_stage:{stage_name}",
    }


def execute_mesh_stage_on_worker(rec: WorkUnitRecord) -> dict[str, Any]:
    payload = rec.payload or {}
    base = {
        "stage_name": rec.stage_name,
        "agent_role": rec.agent_role,
        "run_id": str(rec.run_id),
        "execute_on": "self",
    }
    if not payload.get("mesh_assignment"):
        return {
            **base,
            "ok": False,
            "mesh_ack": False,
            "executed": False,
            "error": "not_mesh_assignment",
        }

    workspace = _resolve_workspace(payload)
    if workspace is None:
        return {
            **base,
            "ok": True,
            "mesh_ack": True,
            "executed": False,
            "reason": "missing_workspace",
        }

    try:
        from nimbusware_compute.mesh_event_replay import (
            baseline_event_ids,
            collect_replay_events,
        )
        from nimbusware_compute.mesh_workspace_merge import (
            diff_workspace_files,
            workspace_file_digests,
        )

        orch = _mesh_orchestrator(workspace)
        before_ids = baseline_event_ids(orch._store, rec.run_id)
        before_digests = (
            workspace_file_digests(workspace) if rec.stage_name in _WRITER_MESH_STAGES else {}
        )
        body = execute_mesh_stage(orch, rec, workspace=workspace)
        executed = body.get("status") != "skipped"
        replay_events = collect_replay_events(orch._store, rec.run_id, before_ids)
        result: dict[str, Any] = {
            **base,
            "ok": True,
            "mesh_ack": True,
            "executed": executed,
            **body,
            "replay_events": replay_events,
        }
        if rec.stage_name in _WRITER_MESH_STAGES:
            after_digests = workspace_file_digests(workspace)
            patch = diff_workspace_files(before_digests, after_digests, workspace)
            if patch:
                result["workspace_files"] = patch
        return result
    except Exception as exc:
        return {
            **base,
            "ok": False,
            "mesh_ack": False,
            "executed": False,
            "error": str(exc),
        }
