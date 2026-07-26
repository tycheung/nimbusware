from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import compute_json_openapi_responses
from broker_client.flags import broker_compute_enabled
from compute.broker_route import map_broker_compute_http_error
from compute.broker_session_status import broker_session_compute_status
from compute.node_store import build_compute_node_store, row_to_public
from compute.work_unit import get_work_unit_queue
from env.env_flags import nimbusware_database_url

router = APIRouter(prefix="/enterprise/fleet-mesh", tags=["enterprise", "compute"])


class FleetMeshStatusResponse(BaseModel):
    """GET fleet-mesh status (COMPUTE peel-aware; sak444-e)."""

    feature: str | None = None
    status: str | None = None
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    queue_depth: int = 0
    via: str | None = None
    error: str | None = None
    session_id: str | None = None


@router.get(
    "/status",
    response_model=FleetMeshStatusResponse,
    response_model_exclude_none=True,
    summary="Fleet mesh status (broker-first; sak444-e)",
    responses=compute_json_openapi_responses(),  # sak492-b / sak518-c
)
def fleet_mesh_status(
    _gate: EnterpriseDep,
    session_id: UUID | None = None,
) -> dict[str, Any]:
    # sak424-e / sak435-b/d / sak436-b/c / sak490-g: broker-first; shared miss map under peel.
    if broker_compute_enabled():
        try:
            return broker_session_compute_status(
                str(session_id) if session_id is not None else None,
                feature="fleet_mesh",
            )
        except Exception as exc:  # noqa: BLE001
            return map_broker_compute_http_error(
                exc,
                feature="fleet_mesh",
                only_msg=(
                    f"fleet_mesh local status unavailable under NIMBUSWARE_BROKER_COMPUTE=2: {exc}"
                ),
                miss_extra={
                    "status": "degraded",
                    "nodes": [],
                    "queue_depth": 0,
                },
            )
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
