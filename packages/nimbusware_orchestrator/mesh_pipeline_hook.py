from __future__ import annotations

from uuid import UUID

from nimbusware_compute.work_unit import get_work_unit_queue
from nimbusware_orchestrator.mesh_scheduler import get_mesh_scheduler

CRITIC_STAGE_NAMES = (
    "security_critique",
    "performance_critique",
    "network_resilience_critique",
)


def mesh_assign_parallel_stages(
    *,
    run_id: UUID,
    stage_names: list[str],
    session_id: UUID | None,
    workload_distribution: str,
    node_ids: list[UUID],
    role_claims: dict[str, str] | None = None,
    parallel_group: str = "writers",
) -> dict[str, UUID | None]:
    sched = get_mesh_scheduler()
    sched.set_mode(workload_distribution or "host_only")
    if session_id is not None and node_ids:
        sched.register_session_nodes(session_id, node_ids)
    assignments = sched.assign(
        parallel_group=parallel_group,
        stage_names=stage_names,
        session_id=session_id,
        claims=role_claims,
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
            payload={"node_id": str(node_id), "mesh_assignment": True},
        )
    return assignments


def mesh_assign_parallel_critics(
    *,
    run_id: UUID,
    session_id: UUID | None,
    workload_distribution: str,
    node_ids: list[UUID],
) -> dict[str, UUID | None]:
    return mesh_assign_parallel_stages(
        run_id=run_id,
        stage_names=list(CRITIC_STAGE_NAMES),
        session_id=session_id,
        workload_distribution=workload_distribution,
        node_ids=node_ids,
        parallel_group="critics",
    )


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
