from __future__ import annotations

import asyncio
import json
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import OptionalUserDep
from nimbusware_api.routes.chat_common import actor_user_id, require_collab_enabled, session_or_404
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_api.user import UserDep
from nimbusware_auth.permissions import enforce_collab_turn_write, require_session_participant
from nimbusware_compute.node_store import build_compute_node_store, default_tenant_id, row_to_public
from nimbusware_env.env_flags import nimbusware_collab_enabled, nimbusware_database_url
from nimbusware_iam.context import resolve_store_tenant_id
from nimbusware_orchestrator.collab_stream_redaction import redact_theater_lines

router = APIRouter(prefix="/chat", tags=["maker"])

_SESSION_SSE_CAP = 96
_STREAM_ROLES = frozenset({"theater", "run_status", "participant", "user", "system"})


def _sse_pack(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def _participant_signature(collab_store: CollabStoreDep, session_id: UUID) -> str:
    rows = collab_store.list_participants(session_id)
    bits = sorted(f"{p.user_id}:{p.role}" for p in rows)
    return "|".join(bits)


@router.get(
    "/sessions/{session_id}/stream",
    responses={404: PROBLEM_RESPONSE_404},
)
def chat_session_stream(
    session_id: UUID,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    request: Request,
    user: OptionalUserDep,
) -> StreamingResponse:
    if nimbusware_collab_enabled():
        require_collab_enabled()
        session_or_404(chat_store, session_id)
        actor = actor_user_id(request, user)
        require_session_participant(
            collab_store,
            session_id=session_id,
            user_id=actor,
            minimum_role="session_read",
        )
    else:
        session_or_404(chat_store, session_id)

    async def generate() -> Any:
        last_fingerprint: str | None = None
        idle = 0
        while idle < 60:
            session = chat_store.get_session(session_id)
            if session is None:
                yield _sse_pack("error", {"code": "chat_session_not_found"})
                return
            turns = chat_store.list_turns(session_id)
            turn_count = len(turns)
            updated = session.updated_at.isoformat()
            part_sig = ""
            participants: list[dict[str, Any]] = []
            if nimbusware_collab_enabled():
                part_sig = _participant_signature(collab_store, session_id)
                participants = [p.to_dict() for p in collab_store.list_participants(session_id)]
            fingerprint = f"{updated}:{turn_count}:{part_sig}"
            if fingerprint != last_fingerprint:
                last_fingerprint = fingerprint
                idle = 0
                lines = [t.to_dict() for t in turns if t.role in _STREAM_ROLES][-_SESSION_SSE_CAP:]
                if nimbusware_collab_enabled():
                    lines = redact_theater_lines(lines)
                yield _sse_pack(
                    "session",
                    {
                        "session_id": str(session_id),
                        "updated_at": updated,
                        "turn_count": turn_count,
                        "theater_lines": lines,
                        "participants": participants,
                    },
                )
            else:
                idle += 1
                yield _sse_pack("heartbeat", {"session_id": str(session_id)})
            await asyncio.sleep(0.5)
        yield _sse_pack("done", {"session_id": str(session_id), "reason": "idle_timeout"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class CommentaryBody(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.post("/sessions/{session_id}/commentary")
def post_session_commentary(
    session_id: UUID,
    body: CommentaryBody,
    request: Request,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    store: StoreDep,
    user: OptionalUserDep,
    _user: UserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    session_or_404(chat_store, session_id)
    actor_id = user.user_id if user is not None else actor_user_id(request, user)
    enforce_collab_turn_write(
        collab_store,
        session_id=session_id,
        user_id=actor_id,
        collab_enabled=True,
    )
    turn = chat_store.append_turn(
        session_id,
        role="participant",
        text=body.text.strip(),
        payload={"kind": "commentary"},
    )
    routes: list[dict[str, str]] = []
    if nimbusware_collab_enabled():
        from nimbusware_maker.collab_discipline_routing import maybe_route_collab_message

        routes = maybe_route_collab_message(
            store,
            chat_store,
            collab_store,
            session_id=session_id,
            message=body.text.strip(),
            actor_user_id=actor_id,
        )
    result: dict[str, Any] = {"turn": turn.to_dict()}
    if routes:
        result["discipline_routes"] = routes
    return result


class DelegateControlBody(BaseModel):
    allow_host_resource_management: bool = False


@router.post("/sessions/{session_id}/compute/delegate-control")
def session_compute_delegate_control(
    session_id: UUID,
    body: DelegateControlBody,
    request: Request,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    user: OptionalUserDep,
    _user: UserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    session_or_404(chat_store, session_id)
    actor_id = user.user_id if user is not None else actor_user_id(request, user)
    require_session_participant(
        collab_store,
        session_id=session_id,
        user_id=actor_id,
        minimum_role="session_write",
    )
    store = build_compute_node_store(nimbusware_database_url())
    row = store.set_delegate_control(
        session_id=session_id,
        user_id=str(actor_id),
        allow_host_resource_management=body.allow_host_resource_management,
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "compute_node_not_found",
                "register compute for this session before delegating control",
            ),
        )
    return {"node": row_to_public(row)}


class SessionOptimizerBody(BaseModel):
    priority: list[str] = Field(default_factory=list)


@router.get("/sessions/{session_id}/optimizer-weights")
def get_session_optimizer_weights(
    session_id: UUID,
    chat_store: ChatStoreDep,
    _user: UserDep,
) -> dict[str, Any]:
    sess = session_or_404(chat_store, session_id)
    from nimbusware_maker.optimizer_weights_store import DEFAULT_OPTIMIZER_WEIGHTS
    from nimbusware_orchestrator.role_claims_mesh import optimizer_weights_from_session_metadata

    meta = sess.metadata if isinstance(sess.metadata, dict) else {}
    priority = meta.get("optimizer_priority")
    if not isinstance(priority, list):
        priority = list(DEFAULT_OPTIMIZER_WEIGHTS.keys())
    weights = optimizer_weights_from_session_metadata(meta)
    return {"priority": priority, "weights": weights}


@router.put("/sessions/{session_id}/optimizer-weights")
def put_session_optimizer_weights(
    session_id: UUID,
    body: SessionOptimizerBody,
    chat_store: ChatStoreDep,
    _user: UserDep,
) -> dict[str, Any]:
    session_or_404(chat_store, session_id)
    from nimbusware_maker.optimizer_weights_store import DEFAULT_OPTIMIZER_WEIGHTS
    from nimbusware_orchestrator.mesh_optimizer import weights_from_priority

    allowed = set(DEFAULT_OPTIMIZER_WEIGHTS.keys())
    priority = [k for k in body.priority if k in allowed]
    if not priority:
        priority = list(DEFAULT_OPTIMIZER_WEIGHTS.keys())
    weights = weights_from_priority(priority)
    sess = chat_store.get_session(session_id)
    meta = dict(sess.metadata if sess and isinstance(sess.metadata, dict) else {})
    meta["optimizer_priority"] = priority
    meta["optimizer_weights"] = weights
    chat_store.update_session(session_id, metadata=meta)
    return {"priority": priority, "weights": weights}


class SessionComputeOptInBody(BaseModel):
    enabled: bool = False
    share_policy: Literal["off", "claim_only", "managed_by_host", "full_auto"] = "off"
    allow_host_resource_management: bool = False
    host_label: str = Field(default="", max_length=200)
    base_url: str = Field(default="http://127.0.0.1:0", max_length=500)


@router.post("/sessions/{session_id}/compute/opt-in")
def session_compute_opt_in(
    session_id: UUID,
    body: SessionComputeOptInBody,
    request: Request,
    chat_store: ChatStoreDep,
    user: OptionalUserDep,
    _user: UserDep,
) -> dict[str, Any]:
    session_or_404(chat_store, session_id)
    actor_id = user.user_id if user is not None else None
    if actor_id is None and nimbusware_collab_enabled():
        actor_id = actor_user_id(request, user)
    store = build_compute_node_store(nimbusware_database_url())
    tid = resolve_store_tenant_id()
    tenant_id = tid if isinstance(tid, UUID) else default_tenant_id()
    node = None
    if body.enabled:
        node = store.register(
            tenant_id=tenant_id,
            user_id=str(actor_id) if actor_id is not None else "",
            display_name=body.host_label or "local",
            host_label=body.host_label,
            base_url=body.base_url,
            session_id=session_id,
            share_policy=body.share_policy,
            allow_host_resource_management=body.allow_host_resource_management,
        )
    return {
        "session_id": str(session_id),
        "enabled": body.enabled,
        "share_policy": body.share_policy,
        "node": row_to_public(node) if node else None,
    }


class ParticipantRoleBindingBody(BaseModel):
    agent_role: str = Field(min_length=1, max_length=128)
    provider_kind: str = Field(default="cloud", max_length=32)
    provider_id: str = Field(min_length=1, max_length=64)
    model_id: str = Field(min_length=1, max_length=256)
    connection_id: str | None = Field(default=None, max_length=128)


@router.get("/sessions/{session_id}/participant-bindings")
def get_participant_bindings(
    session_id: UUID,
    request: Request,
    chat_store: ChatStoreDep,
    user: OptionalUserDep,
    _user: UserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    session_or_404(chat_store, session_id)
    actor_id = user.user_id if user is not None else actor_user_id(request, user)
    sess = chat_store.get_session(session_id)
    meta = dict(sess.metadata if sess and isinstance(sess.metadata, dict) else {})
    from nimbusware_orchestrator.collab_binding_resolver import participant_binding_overrides

    return {
        "user_id": actor_id,
        "roles": participant_binding_overrides(meta, str(actor_id)),
    }


@router.put("/sessions/{session_id}/participant-bindings")
def put_participant_binding(
    session_id: UUID,
    body: ParticipantRoleBindingBody,
    request: Request,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    user: OptionalUserDep,
    _user: UserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    session_or_404(chat_store, session_id)
    actor_id = user.user_id if user is not None else actor_user_id(request, user)
    require_session_participant(collab_store, session_id=session_id, user_id=actor_id)
    sess = chat_store.get_session(session_id)
    meta = dict(sess.metadata if sess and isinstance(sess.metadata, dict) else {})
    from nimbusware_orchestrator.collab_binding_resolver import (
        merge_participant_binding,
        participant_binding_overrides,
    )

    binding = {
        "provider_kind": body.provider_kind,
        "provider_id": body.provider_id,
        "model_id": body.model_id,
    }
    if body.connection_id:
        binding["connection_id"] = body.connection_id
    meta = merge_participant_binding(
        meta,
        user_id=str(actor_id),
        agent_role=body.agent_role,
        binding=binding,
    )
    chat_store.update_session(session_id, metadata=meta)
    return {
        "user_id": actor_id,
        "roles": participant_binding_overrides(meta, str(actor_id)),
    }
