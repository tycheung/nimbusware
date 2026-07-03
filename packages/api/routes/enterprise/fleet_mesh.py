from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter

from api.routes.enterprise.core import EnterpriseDep
from compute.node_store import build_compute_node_store, row_to_public
from compute.work_unit import get_work_unit_queue
from env.env_flags import nimbusware_database_url

router = APIRouter(prefix="/enterprise/fleet-mesh", tags=["enterprise", "compute"])


@router.get("/status")
def fleet_mesh_status(
    _gate: EnterpriseDep,
    session_id: UUID | None = None,
) -> dict[str, Any]:
    store = build_compute_node_store(nimbusware_database_url())
    nodes: list[dict[str, Any]] = []
    if session_id is not None:
        nodes = [row_to_public(row) for row in store.list_for_session(session_id)]
    queue = get_work_unit_queue()
    return {
        "feature": "fleet_mesh",
        "status": "ok",
        "nodes": nodes,
        "queue_depth": queue.queued_count(session_id=session_id),
    }
