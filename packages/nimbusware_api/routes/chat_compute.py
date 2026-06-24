from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import OptionalUserDep
from nimbusware_api.routes.chat_collab_common import actor_user_id, require_collab_enabled
from nimbusware_api.routes.chat_common import session_or_404 as _session_or_404
from nimbusware_api.user import UserDep
from nimbusware_auth.permissions import enforce_collab_turn_write, require_session_participant
from nimbusware_compute.node_store import build_compute_node_store, default_tenant_id, row_to_public
from nimbusware_env.env_flags import nimbusware_collab_enabled, nimbusware_database_url
from nimbusware_iam.context import resolve_store_tenant_id

router = APIRouter(prefix="/chat", tags=["maker"])


class CommentaryBody(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@router.post("/sessions/{session_id}/commentary")
def post_session_commentary(
    session_id: UUID,
    body: CommentaryBody,
    request: Request,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    user: OptionalUserDep,
    _user: UserDep,
) -> dict[str, Any]:
    require_collab_enabled()
    _session_or_404(chat_store, session_id)
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
    return {"turn": turn.to_dict()}


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
    _session_or_404(chat_store, session_id)
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
    sess = _session_or_404(chat_store, session_id)
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
    _session_or_404(chat_store, session_id)
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
    _session_or_404(chat_store, session_id)
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
