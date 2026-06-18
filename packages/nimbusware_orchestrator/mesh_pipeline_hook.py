from __future__ import annotations

from uuid import UUID

from nimbusware_compute.work_unit import get_work_unit_queue
from nimbusware_orchestrator.mesh_scheduler import get_mesh_scheduler


def mesh_assign_parallel_stages(
    *,
    run_id: UUID,
    stage_names: list[str],
    session_id: UUID | None,
    workload_distribution: str,
    node_ids: list[UUID],
    role_claims: dict[str, str] | None = None,
) -> dict[str, UUID | None]:
    sched = get_mesh_scheduler()
    sched.set_mode(workload_distribution or "host_only")
    if session_id is not None and node_ids:
        sched.register_session_nodes(session_id, node_ids)
    assignments = sched.assign(
        parallel_group="writers",
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
