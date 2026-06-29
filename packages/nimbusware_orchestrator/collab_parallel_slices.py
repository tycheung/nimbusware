from __future__ import annotations

from typing import Any
from uuid import UUID

from nimbusware_orchestrator.mesh_pipeline_hook import resolve_mesh_context_for_run


def _distinct_role_claimers(store: Any, run_id: UUID) -> int:
    from nimbusware_orchestrator.role_claims_mesh import role_claims_for_run

    claims = role_claims_for_run(store, run_id)
    return len({str(v).strip() for v in claims.values() if str(v).strip()})


def _participants_with_discipline(collab_store: Any, session_id: UUID) -> int:
    rows = collab_store.list_participants(session_id)
    return sum(1 for row in rows if str(getattr(row, "user_discipline", "") or "").strip())


def collab_mesh_parallel_count(
    run_id: UUID,
    *,
    store: Any,
    collab_store: Any | None = None,
) -> int:
    session_id, workload, node_ids = resolve_mesh_context_for_run(run_id)
    if session_id is None or workload == "host_only" or len(node_ids) < 2:
        return 1
    claimers = _distinct_role_claimers(store, run_id)
    if claimers >= 2:
        return min(2, len(node_ids))
    if collab_store is not None:
        with_discipline = _participants_with_discipline(collab_store, session_id)
        if with_discipline >= 2:
            return min(2, len(node_ids))
    return 1
