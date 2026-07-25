from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.errors import problem
from api.schemas.openapi import PROBLEM_RESPONSE_404
from api.schemas.peel_responses import compute_json_openapi_responses
from api.user import UserDep
from compute.broker_public import (
    broker_node_public,
    broker_work_public,
    caps_from_capabilities,
)
from compute.broker_route import (
    compute_broker_only,
    compute_dual_run_on,
    map_broker_compute_http_error,
    miss,
    refuse_broker_only_http,
)
from compute.node_store import (
    ComputeNodeStore,
    build_compute_node_store,
    default_tenant_id,
    row_to_public,
)
from env.edition import is_enterprise
from env.env_flags import nimbusware_database_url
from iam.context import get_auth_context, resolve_store_tenant_id

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


class WorkUnitEnqueueBody(BaseModel):
    kind: str = Field(default="mesh_stage", max_length=200)
    payload: dict[str, Any] = Field(default_factory=dict)
    run_id: UUID | None = None
    session_id: UUID | None = None
    stage_name: str | None = Field(default=None, max_length=200)
    agent_role: str | None = Field(default=None, max_length=200)
    executor_user_id: str = Field(default="", max_length=200)


class WorkUnitClaimResponse(BaseModel):
    """Claim response: empty poll stays via=broker; miss uses via=broker_miss (`sak440-g`)."""

    work_unit: dict[str, Any] | None = None
    via: Literal["broker", "broker_miss", "local"] | str = "broker"
    error: str | None = None
    status: str | None = None
    feature: str | None = None


class ComputeNodeListResponse(BaseModel):
    """GET /compute/nodes list (`sak441-e`)."""

    nodes: list[dict[str, Any]] = Field(default_factory=list)
    via: str | None = None
    error: str | None = None
    status: str | None = None
    feature: str | None = None


class WorkUnitQueueDepthResponse(BaseModel):
    """GET /compute/work-units/queue (`sak441-e`)."""

    queued: int = 0
    via: str | None = None
    error: str | None = None
    status: str | None = None
    feature: str | None = None


class ComputeNodeWriteResponse(BaseModel):
    """POST register/heartbeat (`sak442-e`)."""

    node: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    status: str | None = None
    feature: str | None = None
    action: str | None = None


class WorkUnitWriteResponse(BaseModel):
    """POST enqueue/complete/terminate-restart (`sak442-e`)."""

    work_unit: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    status: str | None = None
    feature: str | None = None
    action: str | None = None


class WorkUnitClaimBody(BaseModel):
    node_id: UUID
    session_id: UUID | None = None


class WorkUnitCompleteBody(BaseModel):
    status: Literal["ok", "failed", "timeout"] = "ok"
    result: dict[str, Any] | None = None


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


@router.get(
    "/compute/nodes",
    response_model=ComputeNodeListResponse,
    response_model_exclude_none=True,
    summary="List Compute Nodes (broker-first; sak441-e)",
    responses=compute_json_openapi_responses(),  # sak517-g
)
def list_compute_nodes(
    _: UserDep,
    session_id: UUID | None = None,
) -> dict[str, Any]:
    refuse_broker_only_http()
    if compute_dual_run_on():
        try:
            from broker_client.stage_bind.compute import (
                build_compute_list_nodes_payload,
                compute_node_via_broker,
            )
            from compute.broker_session_status import assert_broker_compute_ok

            raw = assert_broker_compute_ok(
                compute_node_via_broker(
                    build_compute_list_nodes_payload(
                        session_id=str(session_id) if session_id else None,
                    )
                ),
                feature="compute_nodes_list",
                list_key="nodes",
            )
            nodes: list[dict[str, Any]] = []
            for item in raw.get("nodes") or []:
                if isinstance(item, dict):
                    nodes.append(broker_node_public(item, session_id=session_id))
            return {"nodes": nodes, "via": "broker"}
        except Exception as exc:  # noqa: BLE001
            # sak431-b / sak436-c / sak437-b: COMPUTE=1 miss — no node_store fallthrough.
            return map_broker_compute_http_error(
                exc,
                feature="compute_nodes_list",
                miss_extra={"nodes": [], "status": "degraded"},
            )
    store = _store()
    if session_id is None:
        return {"nodes": []}
    rows = store.list_for_session(session_id)
    return {"nodes": [row_to_public(r) for r in rows]}


@router.post(
    "/compute/nodes/register",
    response_model=ComputeNodeWriteResponse,
    response_model_exclude_none=True,
    summary="Register Compute Node (broker-first; sak442-e)",
    responses=compute_json_openapi_responses(),  # sak517-g
)
def register_compute_node(body: ComputeNodeRegisterBody, _: UserDep) -> dict[str, Any]:
    refuse_broker_only_http()
    if compute_dual_run_on():
        try:
            from broker_client.stage_bind.compute import (
                build_compute_register_payload,
                compute_node_via_broker,
            )
            from compute.broker_session_status import assert_broker_compute_record_ok

            caps = caps_from_capabilities(body.capabilities)
            if body.allow_host_resource_management:
                caps.append("allow_host_resource_management=true")
            label = body.display_name or body.host_label or "worker"
            raw = assert_broker_compute_record_ok(
                compute_node_via_broker(
                    build_compute_register_payload(
                        label,
                        caps=caps,
                        node_id=str(body.node_id) if body.node_id else None,
                        session_id=str(body.session_id) if body.session_id else None,
                    )
                ),
                feature="compute_nodes_register",
                record_key="node",
            )
            node = raw.get("node") if isinstance(raw.get("node"), dict) else raw
            return {
                "node": broker_node_public(node, session_id=body.session_id),
                "via": "broker",
            }
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            return map_broker_compute_http_error(exc, feature="compute_nodes_register")
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


@router.post(
    "/compute/nodes/{node_id}/heartbeat",
    response_model=ComputeNodeWriteResponse,
    response_model_exclude_none=True,
    summary="Heartbeat Compute Node (broker-first; sak442-e)",
    responses=compute_json_openapi_responses(
        not_found=PROBLEM_RESPONSE_404,
    ),  # sak517-h
)
def heartbeat_compute_node(
    node_id: UUID,
    body: ComputeNodeHeartbeatBody,
    _: UserDep,
) -> dict[str, Any]:
    refuse_broker_only_http()
    if compute_dual_run_on():
        try:
            from broker_client.stage_bind.compute import (
                build_compute_heartbeat_payload,
                compute_node_via_broker,
            )
            from compute.broker_session_status import assert_broker_compute_record_ok

            raw = assert_broker_compute_record_ok(
                compute_node_via_broker(build_compute_heartbeat_payload(str(node_id))),
                feature="compute_nodes_heartbeat",
                record_key="node",
            )
            node = raw.get("node") if isinstance(raw.get("node"), dict) else raw
            pub = broker_node_public(node)
            if body.status:
                pub["status"] = body.status
            return {"node": pub, "via": "broker"}
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            return map_broker_compute_http_error(exc, feature="compute_nodes_heartbeat")
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


@router.post(
    "/compute/work-units/enqueue",
    response_model=WorkUnitWriteResponse,
    response_model_exclude_none=True,
    summary="Enqueue Work Unit (broker-first; sak442-e)",
    responses=compute_json_openapi_responses(),
)
def enqueue_work_unit(body: WorkUnitEnqueueBody, _: UserDep) -> dict[str, Any]:
    """Broker-first enqueue (`sak431-a`)."""
    refuse_broker_only_http()
    payload = dict(body.payload)
    if body.run_id is not None:
        payload.setdefault("run_id", str(body.run_id))
    if body.session_id is not None:
        payload.setdefault("session_id", str(body.session_id))
    if body.stage_name:
        payload.setdefault("stage_name", body.stage_name)
    if body.agent_role:
        payload.setdefault("agent_role", body.agent_role)
    if body.executor_user_id:
        payload.setdefault("executor_user_id", body.executor_user_id)

    if compute_dual_run_on():
        try:
            from broker_client.stage_bind.compute import (
                build_compute_enqueue_payload,
                compute_work_via_broker,
            )
            from compute.broker_session_status import assert_broker_compute_record_ok

            kind = body.kind or body.stage_name or "mesh_stage"
            raw = assert_broker_compute_record_ok(
                compute_work_via_broker(build_compute_enqueue_payload(kind, payload)),
                feature="compute_enqueue",
                record_key="work",
            )
            work = raw.get("work") if isinstance(raw.get("work"), dict) else raw
            return {
                "work_unit": broker_work_public(work),
                "via": "broker",
                "action": "enqueue",
            }
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            return map_broker_compute_http_error(
                exc, feature="compute_enqueue", miss_extra={"work_unit": None}
            )

    from compute.work_unit import get_work_unit_queue, work_unit_to_public

    if body.run_id is None:
        raise HTTPException(
            status_code=422,
            detail=problem("run_id_required", "run_id required for local enqueue"),
        )
    rec = get_work_unit_queue().enqueue(
        run_id=body.run_id,
        session_id=body.session_id,
        stage_name=body.stage_name or body.kind or "mesh_stage",
        agent_role=body.agent_role or body.stage_name or body.kind or "",
        executor_user_id=body.executor_user_id,
        payload=payload,
    )
    return {"work_unit": work_unit_to_public(rec)}


@router.post(
    "/compute/work-units/claim",
    response_model=WorkUnitClaimResponse,
    response_model_exclude_none=True,
    summary="Claim Work Unit (broker-first; empty→via=broker; sak440-g)",
    responses=compute_json_openapi_responses(),  # sak517-h
)
def claim_work_unit(body: WorkUnitClaimBody, _: UserDep) -> dict[str, Any]:
    refuse_broker_only_http()
    if compute_dual_run_on():
        try:
            from broker_client.stage_bind.compute import (
                build_compute_claim_payload,
                compute_work_via_broker,
            )
            from compute.broker_session_status import normalize_claim_work_response

            # sak443-b: direct normalize + miss map (no try_broker_call soft path).
            raw = normalize_claim_work_response(
                compute_work_via_broker(build_compute_claim_payload(str(body.node_id))),
                feature="compute_claim",
            )
            work = raw.get("work")
            if isinstance(work, dict):
                return {"work_unit": broker_work_public(work), "via": "broker"}
            return {"work_unit": None, "via": "broker"}
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            return map_broker_compute_http_error(
                exc, feature="compute_claim", miss_extra={"work_unit": None}
            )
    from compute.work_unit import get_work_unit_queue, work_unit_to_public

    rec = get_work_unit_queue().dequeue(
        session_id=body.session_id,
        node_id=body.node_id,
    )
    if rec is None:
        return {"work_unit": None}
    return {"work_unit": work_unit_to_public(rec)}


@router.get(
    "/compute/work-units/queue",
    response_model=WorkUnitQueueDepthResponse,
    response_model_exclude_none=True,
    summary="Work Unit Queue Depth (broker-first; sak441-e)",
    responses=compute_json_openapi_responses(),  # sak517-i
)
def work_unit_queue_depth(
    _: UserDep,
    session_id: UUID | None = None,
) -> dict[str, Any]:
    refuse_broker_only_http()
    if compute_dual_run_on():
        try:
            from broker_client.stage_bind.compute import (
                build_compute_list_payload,
                compute_work_via_broker,
                queue_depth_for_session,
            )
            from compute.broker_session_status import assert_broker_compute_ok

            raw = assert_broker_compute_ok(
                compute_work_via_broker(
                    build_compute_list_payload(status="queued", limit=200)
                ),
                feature="compute_queue_depth",
                list_key="work",
            )
            queued = 0
            if isinstance(raw.get("work"), list):
                items = [w for w in raw["work"] if isinstance(w, dict)]
                queued = queue_depth_for_session(
                    items, str(session_id) if session_id is not None else None
                )
            return {
                "queued": queued,
                "session_id": str(session_id) if session_id else None,
                "via": "broker",
                "status": "ok",
            }
        except Exception as exc:  # noqa: BLE001
            return map_broker_compute_http_error(
                exc,
                feature="compute_queue_depth",
                miss_extra={
                    "queued": 0,
                    "session_id": str(session_id) if session_id else None,
                    "status": "degraded",
                },
            )
    from compute.work_unit import get_work_unit_queue

    queue = get_work_unit_queue()
    return {
        "queued": queue.queued_count(session_id=session_id),
        "session_id": str(session_id) if session_id else None,
    }


@router.post(
    "/compute/work-units/{work_unit_id}/complete",
    response_model=WorkUnitWriteResponse,
    response_model_exclude_none=True,
    summary="Complete Work Unit (broker-first; sak442-e)",
    responses=compute_json_openapi_responses(
        not_found=PROBLEM_RESPONSE_404,
    ),  # sak517-i
)
def complete_work_unit(
    work_unit_id: UUID,
    body: WorkUnitCompleteBody,
    _: UserDep,
) -> dict[str, Any]:
    refuse_broker_only_http()
    if compute_dual_run_on():
        try:
            from broker_client.stage_bind.compute import (
                build_compute_complete_payload,
                build_compute_get_payload,
                compute_work_via_broker,
            )
            from compute.broker_node_match import node_id_from_broker_record
            from compute.broker_session_status import assert_broker_compute_record_ok

            result = dict(body.result or {})
            if body.status != "ok":
                result.setdefault("status", body.status)
            got = assert_broker_compute_record_ok(
                compute_work_via_broker(build_compute_get_payload(str(work_unit_id))),
                feature="compute_complete.get",
                record_key="work",
            )
            existing = got.get("work") if isinstance(got.get("work"), dict) else got
            node_id = ""
            if isinstance(existing, dict) and existing.get("id"):
                claimed = existing.get("claimed_by")
                if isinstance(claimed, dict):
                    node_id = node_id_from_broker_record(claimed)
                elif claimed:
                    node_id = str(claimed)
                elif existing.get("node_id"):
                    node_id = str(existing["node_id"])
            if not node_id:
                raise RuntimeError("broker_miss: work unit missing claimer on broker")
            raw = assert_broker_compute_record_ok(
                compute_work_via_broker(
                    build_compute_complete_payload(
                        work_id=str(work_unit_id),
                        node_id=node_id,
                        result=result,
                    )
                ),
                feature="compute_complete",
                record_key="work",
            )
            work = raw.get("work") if isinstance(raw.get("work"), dict) else raw
            return {"work_unit": broker_work_public(work), "via": "broker"}
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            return map_broker_compute_http_error(
                exc, feature="compute_complete", miss_extra={"work_unit": None}
            )
    from compute.work_unit import get_work_unit_queue, work_unit_to_public
    from compute.worker_policy import sanitize_work_unit_payload

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


@router.post(
    "/compute/work-units/{work_unit_id}/terminate-restart",
    response_model=WorkUnitWriteResponse,
    response_model_exclude_none=True,
    summary="Terminate Restart Work Unit (broker-first; sak442-e)",
    responses=compute_json_openapi_responses(
        not_found=PROBLEM_RESPONSE_404,
    ),  # sak518-a
)
def terminate_restart_work_unit(work_unit_id: UUID, _: UserDep) -> dict[str, Any]:
    refuse_broker_only_http()
    if compute_dual_run_on():
        try:
            from broker_client.stage_bind.compute import terminate_restart_via_broker
            from compute.broker_session_status import assert_broker_compute_record_ok

            raw = assert_broker_compute_record_ok(
                terminate_restart_via_broker(str(work_unit_id)),
                feature="compute_terminate_restart",
                record_key="work",
            )
            work = raw.get("work") if isinstance(raw.get("work"), dict) else raw
            return {
                "work_unit": broker_work_public(work),
                "via": "broker",
                "action": "requeue",
            }
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            return map_broker_compute_http_error(
                exc,
                feature="compute_terminate_restart",
                miss_extra={"work_unit": None, "action": "requeue"},
            )
    from compute.work_unit import get_work_unit_queue, work_unit_to_public

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
