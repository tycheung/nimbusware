from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep, ProjectStoreDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes import chat_start
from nimbusware_api.routes.chat_common import (
    ActiveLeafBody,
    AppendTurnBody,
    ChatGraphResponse,
    ChatMessageBody,
    ChatMessageResponse,
    ChatSessionResponse,
    ClassificationResponse,
    ClassifyIntentBody,
    CreateChatSessionBody,
    ForkChatBody,
    SwitchModeBody,
    project_metadata,
)
from nimbusware_api.routes.chat_handlers import (
    chat_http_error as _chat_http_error,
)
from nimbusware_api.routes.chat_handlers import (
    platform_hints as _platform_hints,
)
from nimbusware_api.routes.chat_handlers import (
    session_or_404 as _session_or_404,
)
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_api.routes.auth import OptionalUserDep
from nimbusware_api.routes.chat_collab_common import actor_user_id
from nimbusware_api.user import UserDep
from nimbusware_auth.permissions import enforce_collab_turn_write
from nimbusware_env.env_flags import nimbusware_collab_enabled
from nimbusware_maker.chat_service import (
    classification_dict,
    session_response,
    switch_mode_rationale,
)
from nimbusware_maker.intent_classifier import WorkType, classify_intent
from nimbusware_orchestrator.model_binding_swap import (
    append_model_binding_override,
    append_role_claim,
    append_role_release,
)
from nimbusware_compute.node_store import build_compute_node_store, default_tenant_id, row_to_public
from nimbusware_env.env_flags import nimbusware_database_url
from nimbusware_iam.context import resolve_store_tenant_id

router = APIRouter(prefix="/chat", tags=["maker"])
router.include_router(chat_start.router)


@router.post("/sessions", response_model=ChatSessionResponse)
def create_chat_session(
    body: CreateChatSessionBody,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    project_store: ProjectStoreDep,
    user: OptionalUserDep,
    _user: UserDep,
) -> ChatSessionResponse:
    try:
        project_uuid = UUID(str(body.project_id).strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "project_id must be a UUID"),
        ) from exc
    project_metadata(project_store, project_uuid)
    host_id = user.user_id if (nimbusware_collab_enabled() and user is not None) else None
    metadata = {"folder": body.folder} if body.folder else None
    session = chat_store.create_session(
        project_id=project_uuid,
        host_user_id=host_id,
        metadata=metadata,
    )
    if nimbusware_collab_enabled() and host_id is not None:
        collab_store.add_participant(
            session_id=session.session_id,
            user_id=host_id,
            role="session_admin",
        )
    return ChatSessionResponse(**session_response(chat_store, session))


@router.get("/sessions", response_model=list[ChatSessionResponse])
def list_chat_sessions(
    project_id: UUID,
    chat_store: ChatStoreDep,
    project_store: ProjectStoreDep,
    _user: UserDep,
) -> list[ChatSessionResponse]:
    project_metadata(project_store, project_id)
    sessions = chat_store.list_sessions(project_id=project_id)
    return [ChatSessionResponse(**session_response(chat_store, s)) for s in sessions]


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_chat_session(
    session_id: UUID,
    *,
    request: Request,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    user: OptionalUserDep,
    _user: UserDep,
    include_turns: bool = Query(default=False),
) -> ChatSessionResponse:
    session = _session_or_404(chat_store, session_id)
    payload = session_response(chat_store, session, include_turns=include_turns)
    if nimbusware_collab_enabled():
        payload["participants"] = [
            p.to_dict() for p in collab_store.list_participants(session_id)
        ]
        if user is not None:
            part = collab_store.get_participant(session_id, user.user_id)
            if part is not None:
                payload["my_participant_role"] = part.role
        else:
            uid = None
            try:
                uid = actor_user_id(request, user)
            except HTTPException:
                uid = None
            if uid is not None:
                part = collab_store.get_participant(session_id, uid)
                if part is not None:
                    payload["my_participant_role"] = part.role
    return ChatSessionResponse(**payload)


@router.get(
    "/sessions/{session_id}/graph",
    response_model=ChatGraphResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_chat_graph(session_id: UUID, chat_store: ChatStoreDep, _user: UserDep) -> ChatGraphResponse:
    _session_or_404(chat_store, session_id)
    try:
        graph = chat_store.get_graph(session_id)
    except KeyError as exc:
        raise _chat_http_error(exc) from exc
    return ChatGraphResponse(**graph)


@router.post(
    "/sessions/{session_id}/fork",
    response_model=ChatSessionResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def fork_chat_session(
    session_id: UUID,
    body: ForkChatBody,
    chat_store: ChatStoreDep,
    _user: UserDep,
) -> ChatSessionResponse:
    _session_or_404(chat_store, session_id)
    try:
        turn_id = UUID(body.turn_id)
        session = chat_store.fork_at_turn(session_id, turn_id)
    except (KeyError, ValueError) as exc:
        raise _chat_http_error(exc) from exc
    return ChatSessionResponse(**session_response(chat_store, session, include_turns=True))


@router.put(
    "/sessions/{session_id}/active-leaf",
    response_model=ChatSessionResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def set_chat_active_leaf(
    session_id: UUID,
    body: ActiveLeafBody,
    chat_store: ChatStoreDep,
    _user: UserDep,
) -> ChatSessionResponse:
    _session_or_404(chat_store, session_id)
    try:
        leaf = UUID(body.leaf_turn_id)
        session = chat_store.set_active_leaf(session_id, leaf)
    except (KeyError, ValueError) as exc:
        raise _chat_http_error(exc) from exc
    return ChatSessionResponse(**session_response(chat_store, session, include_turns=True))


@router.post(
    "/sessions/{session_id}/turns",
    response_model=ChatMessageResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def append_chat_turn(
    session_id: UUID,
    body: AppendTurnBody,
    request: Request,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    project_store: ProjectStoreDep,
    user: OptionalUserDep,
    _user: UserDep,
) -> ChatMessageResponse:
    session = _session_or_404(chat_store, session_id)
    actor_id = user.user_id if user is not None else None
    if actor_id is None and nimbusware_collab_enabled():
        try:
            actor_id = actor_user_id(request, user)
        except HTTPException:
            actor_id = None
    enforce_collab_turn_write(
        collab_store,
        session_id=session_id,
        user_id=actor_id,
        collab_enabled=nimbusware_collab_enabled(),
    )
    project_uuid = UUID(str(session.project_id))
    meta = project_metadata(project_store, project_uuid)
    result = classify_intent(
        body.text,
        attachments=body.attachments,
        project_metadata=meta,
        platform_hints=_platform_hints(),
    )
    try:
        turn = chat_store.append_turn(
            session_id,
            role=body.role,
            text=body.text,
            payload={"attachments": body.attachments},
        )
        session = chat_store.update_session(
            session_id,
            last_classification=classification_dict(result),
        )
        classifier_turn = chat_store.append_turn(
            session_id,
            role="classifier",
            text=result.rationale,
            payload={"classification": classification_dict(result)},
            work_type=result.work_type.value,
            work_type_source="classifier",
        )
    except (KeyError, ValueError) as exc:
        raise _chat_http_error(exc) from exc
    message = {
        "role": "user",
        "text": body.text,
        "attachments": body.attachments,
        "turn_id": str(turn.turn_id),
        "posted_at": turn.posted_at.isoformat() if turn.posted_at else None,
    }
    return ChatMessageResponse(
        message=message,
        classification=classification_dict(result),
        turn=classifier_turn.to_dict(),
    )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def post_chat_message(
    session_id: UUID,
    body: ChatMessageBody,
    request: Request,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    project_store: ProjectStoreDep,
    user: OptionalUserDep,
    _user: UserDep,
) -> ChatMessageResponse:
    return append_chat_turn(
        session_id,
        AppendTurnBody(text=body.text, attachments=body.attachments),
        request,
        chat_store,
        collab_store,
        project_store,
        user,
        _user,
    )


@router.post(
    "/sessions/{session_id}/turns/{turn_id}/switch-mode",
    response_model=ChatSessionResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def switch_chat_mode(
    session_id: UUID,
    turn_id: UUID,
    body: SwitchModeBody,
    chat_store: ChatStoreDep,
    _user: UserDep,
) -> ChatSessionResponse:
    session = _session_or_404(chat_store, session_id)
    try:
        work_type = WorkType(body.work_type.strip().lower())
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_request",
                "work_type must be one of quick, patch, slice, campaign, factory",
            ),
        ) from exc
    prior = session.work_type_override or ((session.last_classification or {}).get("work_type"))
    rationale = body.rationale or switch_mode_rationale(
        str(prior) if prior else None, work_type.value
    )
    try:
        chat_store.fork_at_turn(session_id, turn_id)
        payload: dict[str, Any] = {
            "from_work_type": prior,
            "to_work_type": work_type.value,
        }
        if body.replay_from_seq is not None:
            payload["replay_from_seq"] = body.replay_from_seq
        if body.align_run_replay:
            payload["align_run_replay"] = True
        chat_store.append_turn(
            session_id,
            role="work_type_switch",
            text=rationale,
            payload=payload,
            work_type=work_type.value,
            work_type_source="mode_switch",
        )
        session = chat_store.update_session(
            session_id,
            work_type_override=work_type.value,
        )
    except (KeyError, ValueError) as exc:
        raise _chat_http_error(exc) from exc
    return ChatSessionResponse(**session_response(chat_store, session, include_turns=True))


@router.post("/classify", response_model=ClassificationResponse)
def classify_chat_intent(
    body: ClassifyIntentBody,
    project_store: ProjectStoreDep,
    _user: UserDep,
) -> ClassificationResponse:
    meta: dict[str, Any] | None = None
    if body.project_id and str(body.project_id).strip():
        try:
            project_uuid = UUID(str(body.project_id).strip())
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=problem("invalid_request", "project_id must be a UUID"),
            ) from exc
        meta = project_metadata(project_store, project_uuid)
    result = classify_intent(
        body.message,
        attachments=body.attachments,
        project_metadata=meta,
        platform_hints=_platform_hints(body.platform_hints),
    )
    return ClassificationResponse(classification=classification_dict(result))


class SessionModelBindingSwapBody(BaseModel):
    run_id: UUID
    agent_role: str = Field(min_length=1, max_length=120)
    provider_id: str = Field(min_length=1, max_length=80)
    provider_kind: str = Field(default="local", pattern="^(local|cloud)$")
    model_id: str = Field(min_length=1, max_length=200)


@router.post(
    "/sessions/{session_id}/model-bindings/swap",
    response_model=ChatMessageResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def session_model_binding_swap(
    session_id: UUID,
    body: SessionModelBindingSwapBody,
    chat_store: ChatStoreDep,
    store: StoreDep,
    _user: UserDep,
) -> ChatMessageResponse:
    _session_or_404(chat_store, session_id)
    if not store.list_run_events(str(body.run_id)):
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(body.run_id)}),
        )
    payload = append_model_binding_override(
        store,
        body.run_id,
        agent_role=body.agent_role,
        provider_id=body.provider_id,
        provider_kind=body.provider_kind,
        model_id=body.model_id,
    )
    label = f"{body.agent_role} → {body.model_id} ({body.provider_id})"
    turn = chat_store.append_turn(
        session_id,
        role="system",
        text=f"Model swap: {label}",
        payload={"model_swap": payload},
    )
    message = {
        "role": "system",
        "text": turn.text,
        "turn_id": str(turn.turn_id),
        "posted_at": turn.posted_at.isoformat() if turn.posted_at else None,
        "model_swap": payload,
    }
    return ChatMessageResponse(
        message=message,
        classification={"work_type": "system", "rationale": "model_swap"},
        turn=turn.to_dict(),
    )


class SessionRoleClaimBody(BaseModel):
    run_id: UUID
    agent_role: str = Field(min_length=1, max_length=120)
    provider_id: str = Field(min_length=1, max_length=80)
    model_id: str = Field(min_length=1, max_length=200)


@router.post("/sessions/{session_id}/role-claims")
def session_role_claim(
    session_id: UUID,
    body: SessionRoleClaimBody,
    chat_store: ChatStoreDep,
    store: StoreDep,
    _user: UserDep,
) -> dict[str, Any]:
    _session_or_404(chat_store, session_id)
    if not store.list_run_events(str(body.run_id)):
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(body.run_id)}),
        )
    payload = append_role_claim(
        store,
        body.run_id,
        agent_role=body.agent_role,
        provider_id=body.provider_id,
        model_id=body.model_id,
    )
    chat_store.append_turn(
        session_id,
        role="system",
        text=f"Role claimed: {body.agent_role} → {body.model_id}",
        payload={"role_claim": payload},
    )
    return {"ok": True, "event": "workload.role_claimed", "payload": payload}


@router.delete("/sessions/{session_id}/role-claims/{agent_role}")
def session_role_release(
    session_id: UUID,
    agent_role: str,
    chat_store: ChatStoreDep,
    store: StoreDep,
    _user: UserDep,
    run_id: UUID | None = Query(default=None),
) -> dict[str, Any]:
    _session_or_404(chat_store, session_id)
    resolved_run_id = run_id
    if resolved_run_id is None:
        sess = chat_store.get_session(session_id)
        resolved_run_id = sess.run_id
    if resolved_run_id is None or not store.list_run_events(str(resolved_run_id)):
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found"),
        )
    payload = append_role_release(store, resolved_run_id, agent_role=agent_role)
    chat_store.append_turn(
        session_id,
        role="system",
        text=f"Role released: {agent_role}",
        payload={"role_release": payload},
    )
    return {"ok": True, "event": "workload.role_released", "payload": payload}


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
    chat_store: ChatStoreDep,
    _user: UserDep,
) -> dict[str, Any]:
    """Stub D4 — link session participant to compute node registry."""
    _session_or_404(chat_store, session_id)
    store = build_compute_node_store(nimbusware_database_url())
    tid = resolve_store_tenant_id()
    tenant_id = tid if isinstance(tid, UUID) else default_tenant_id()
    node = None
    if body.enabled:
        node = store.register(
            tenant_id=tenant_id,
            user_id="",
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
