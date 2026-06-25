from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.errors import problem
from nimbusware_api.user import UserDep
from nimbusware_compute.node_store import (
    ComputeNodeStore,
    build_compute_node_store,
    default_tenant_id,
    row_to_public,
)
from nimbusware_env.edition import is_enterprise
from nimbusware_env.env_flags import nimbusware_database_url
from nimbusware_iam.context import get_auth_context, resolve_store_tenant_id

router = APIRouter(tags=["compute"])


class ComputeNodeRegisterBody(BaseModel):
    node_id: UUID | None = None
    session_id: UUID | None = None
    display_name: str = Field(default="", max_length=200)
    host_label: str = Field(default="", max_length=200)
    base_url: str = Field(min_length=1, max_length=500)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    share_policy: Literal["off", "claim_only", "managed_by_host", "full_auto"] = "off"
    allow_host_resource_management: bool = False


class ComputeNodeHeartbeatBody(BaseModel):
    status: Literal["unknown", "online", "degraded", "offline"] | None = None
    capabilities: dict[str, Any] | None = None


def _connection_user_id() -> str:
    if not is_enterprise():
        return ""
    ctx = get_auth_context()
    if ctx is None:
        return ""
    return str(ctx.key_id)


def _tenant_uuid() -> UUID:
    tid = resolve_store_tenant_id()
    return tid if isinstance(tid, UUID) else default_tenant_id()


def _store() -> ComputeNodeStore:
    return build_compute_node_store(nimbusware_database_url())


@router.get("/compute/nodes")
def list_compute_nodes(
    _: UserDep,
    session_id: UUID | None = None,
) -> dict[str, Any]:
    store = _store()
    if session_id is None:
        return {"nodes": []}
    rows = store.list_for_session(session_id)
    return {"nodes": [row_to_public(r) for r in rows]}


@router.post("/compute/nodes/register")
def register_compute_node(body: ComputeNodeRegisterBody, _: UserDep) -> dict[str, Any]:
    store = _store()
    row = store.register(
        node_id=body.node_id,
        tenant_id=_tenant_uuid(),
        user_id=_connection_user_id(),
        display_name=body.display_name or body.host_label,
        host_label=body.host_label,
        base_url=body.base_url,
        capabilities=body.capabilities,
        session_id=body.session_id,
        share_policy=body.share_policy,
        allow_host_resource_management=body.allow_host_resource_management,
    )
    return {"node": row_to_public(row)}


@router.post("/compute/nodes/{node_id}/heartbeat")
def heartbeat_compute_node(
    node_id: UUID,
    body: ComputeNodeHeartbeatBody,
    _: UserDep,
) -> dict[str, Any]:
    store = _store()
    row = store.heartbeat(
        node_id,
        status=body.status,
        capabilities=body.capabilities,
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=problem("not_found", "compute node not found"),
        )
    return {"node": row_to_public(row)}


class WorkUnitClaimBody(BaseModel):
    node_id: UUID
    session_id: UUID | None = None


class WorkUnitCompleteBody(BaseModel):
    status: Literal["ok", "failed", "timeout"] = "ok"
    result: dict[str, Any] | None = None


@router.post("/compute/work-units/claim")
def claim_work_unit(body: WorkUnitClaimBody, _: UserDep) -> dict[str, Any]:
    from nimbusware_compute.work_unit import get_work_unit_queue, work_unit_to_public

    rec = get_work_unit_queue().dequeue(
        session_id=body.session_id,
        node_id=body.node_id,
    )
    if rec is None:
        return {"work_unit": None}
    return {"work_unit": work_unit_to_public(rec)}


@router.get("/compute/work-units/queue")
def work_unit_queue_depth(
    _: UserDep,
    session_id: UUID | None = None,
) -> dict[str, Any]:
    from nimbusware_compute.work_unit import get_work_unit_queue

    queue = get_work_unit_queue()
    return {
        "queued": queue.queued_count(session_id=session_id),
        "session_id": str(session_id) if session_id else None,
    }


@router.post("/compute/work-units/{work_unit_id}/complete")
def complete_work_unit(
    work_unit_id: UUID,
    body: WorkUnitCompleteBody,
    _: UserDep,
) -> dict[str, Any]:
    from nimbusware_compute.work_unit import get_work_unit_queue, work_unit_to_public
    from nimbusware_compute.worker_policy import sanitize_work_unit_payload

    safe_result = sanitize_work_unit_payload(body.result) if body.result is not None else None
    rec = get_work_unit_queue().complete(
        work_unit_id,
        status=body.status,
        result=safe_result,
    )
    if rec is None:
        raise HTTPException(
            status_code=404,
            detail=problem("not_found", "work unit not found"),
        )
    return {"work_unit": work_unit_to_public(rec)}


@router.post("/compute/work-units/{work_unit_id}/terminate-restart")
def terminate_restart_work_unit(work_unit_id: UUID, _: UserDep) -> dict[str, Any]:
    from nimbusware_compute.work_unit import get_work_unit_queue, work_unit_to_public

    rec = get_work_unit_queue().terminate_restart(work_unit_id)
    if rec is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "not_found",
                "work unit not found or already finished",
            ),
        )
    return {"work_unit": work_unit_to_public(rec)}
