from __future__ import annotations

from pathlib import Path
from uuid import UUID

from nimbusware_compute.work_unit import get_work_unit_queue
from nimbusware_orchestrator.mesh_scheduler import get_mesh_scheduler
from nimbusware_orchestrator.role_claims_mesh import stage_role_claims

CRITIC_STAGE_NAMES = (
    "security_critique",
    "performance_critique",
    "network_resilience_critique",
)

_WRITER_STAGE_TAXONOMY: dict[str, str] = {
    "implementation": "backend_writer",
    "test_writer": "test_writer",
    "frontend_writer": "frontend_writer",
    "plan": "planner",
}


def _mesh_enqueue_payload(
    node_id: UUID,
    *,
    stage_name: str,
    workspace: Path | str | None = None,
    workflow_profile: str | None = None,
) -> dict[str, str | bool]:
    payload: dict[str, str | bool] = {
        "node_id": str(node_id),
        "mesh_assignment": True,
    }
    if workspace is not None:
        payload["workspace"] = str(workspace)
    if workflow_profile:
        payload["workflow_profile"] = workflow_profile
    taxonomy = _WRITER_STAGE_TAXONOMY.get(stage_name)
    if taxonomy is not None:
        payload["taxonomy_key"] = taxonomy
    return payload


def _executor_user_for_stage(stage_name: str, role_claims: dict[str, str] | None) -> str:
    if not role_claims:
        return ""
    tax = _WRITER_STAGE_TAXONOMY.get(stage_name, stage_name)
    return role_claims.get(tax) or role_claims.get(stage_name, "")


def mesh_assign_parallel_stages(
    *,
    run_id: UUID,
    stage_names: list[str],
    session_id: UUID | None,
    workload_distribution: str,
    node_ids: list[UUID],
    role_claims: dict[str, str] | None = None,
    node_users: dict[UUID, str] | None = None,
    node_capabilities: dict[UUID, dict[str, object]] | None = None,
    optimizer_weights: dict[str, float] | None = None,
    parallel_group: str = "writers",
    workspace: Path | str | None = None,
    workflow_profile: str | None = None,
) -> dict[str, UUID | None]:
    sched = get_mesh_scheduler()
    sched.set_mode(workload_distribution or "host_only")
    if session_id is not None and node_ids:
        sched.register_session_nodes(
            session_id,
            node_ids,
            node_users=node_users,
            node_capabilities=node_capabilities,
            optimizer_weights=optimizer_weights,
        )
    assignments = sched.assign(
        parallel_group=parallel_group,
        stage_names=stage_names,
        session_id=session_id,
        claims=stage_role_claims(role_claims),
    )
    if session_id is None or workload_distribution == "host_only":
        return assignments
    queue = get_work_unit_queue()
    for stage_name, node_id in assignments.items():
        if node_id is None:
            continue
        queue.enqueue(
            run_id=run_id,
            session_id=session_id,
            stage_name=stage_name,
            agent_role=stage_name,
            executor_user_id=_executor_user_for_stage(stage_name, role_claims),
            payload=_mesh_enqueue_payload(
                node_id,
                stage_name=stage_name,
                workspace=workspace,
                workflow_profile=workflow_profile,
            ),
        )
    return assignments


def mesh_assign_parallel_critics(
    *,
    run_id: UUID,
    session_id: UUID | None,
    workload_distribution: str,
    node_ids: list[UUID],
    workspace: Path | str | None = None,
    workflow_profile: str | None = None,
) -> dict[str, UUID | None]:
    return mesh_assign_parallel_stages(
        run_id=run_id,
        stage_names=list(CRITIC_STAGE_NAMES),
        session_id=session_id,
        workload_distribution=workload_distribution,
        node_ids=node_ids,
        parallel_group="critics",
        workspace=workspace,
        workflow_profile=workflow_profile,
    )


def mesh_assign_campaign_slices(
    *,
    run_id: UUID,
    slice_ids: list[str],
    session_id: UUID | None,
    workload_distribution: str,
    node_ids: list[UUID],
    workspace: Path | str | None = None,
    workflow_profile: str | None = None,
) -> dict[str, UUID | None]:
    stage_names = [f"campaign.slice:{sid}" for sid in slice_ids]
    raw = mesh_assign_parallel_stages(
        run_id=run_id,
        stage_names=stage_names,
        session_id=session_id,
        workload_distribution=workload_distribution,
        node_ids=node_ids,
        parallel_group="campaign_slices",
        workspace=workspace,
        workflow_profile=workflow_profile,
    )
    return {sid: raw.get(f"campaign.slice:{sid}") for sid in slice_ids}


def resolve_mesh_context_for_run(run_id: UUID) -> tuple[UUID | None, str, list[UUID]]:
    try:
        from nimbusware_compute.node_store import build_compute_node_store
        from nimbusware_env.env_flags import nimbusware_database_url
        from nimbusware_maker.chat_store import build_chat_store

        chat_store = build_chat_store(nimbusware_database_url())
        sess = chat_store.find_session_by_run_id(run_id)
        if sess is None:
            return None, "host_only", []
        workload = sess.workload_distribution or "host_only"
        node_store = build_compute_node_store(nimbusware_database_url())
        rows = node_store.list_for_session(sess.session_id)
        node_ids = [r.node_id for r in rows if r.status in {"online", "degraded"}]
        return sess.session_id, workload, node_ids
    except Exception:
        return None, "host_only", []


__all__ = [
    "CRITIC_STAGE_NAMES",
    "mesh_assign_campaign_slices",
    "mesh_assign_parallel_critics",
    "mesh_assign_parallel_stages",
    "resolve_mesh_context_for_run",
]
