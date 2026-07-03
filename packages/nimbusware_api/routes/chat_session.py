from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep, OrchDep, ProjectStoreDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep, OptionalUserDep
from nimbusware_api.routes.chat_common import (
    StartChatSessionBody,
    StartChatSessionResponse,
    chat_http_error,
    maybe_apply_chat_replay_alignment,
    patch_context_payload,
    requirements_payload,
    resolve_workflow_profile,
    start_campaign,
    start_run,
)
from nimbusware_api.routes.chat_service import (
    collab_session_actor,
    session_or_404,
)
from nimbusware_api.routes.runs.create import enforce_discovery_gate
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_api.user import UserDep
from nimbusware_auth.permissions import require_session_participant
from nimbusware_env.env_flags import env_str, nimbusware_collab_enabled, nimbusware_database_url
from nimbusware_maker.archetype_surface_defaults import manifest_for_archetype
from nimbusware_maker.autopilot_defer_matrix import autopilot_may_auto_defer
from nimbusware_maker.chat_service import (
    requirements_from_path,
    resolve_work_type,
    resolve_work_type_source,
)
from nimbusware_maker.intent_classifier import WorkType
from nimbusware_maker.scope_discovery import (
    attach_discovery_summary,
    enrich_scope_surface_bindings,
    recommend_for_me,
    scope_confirm,
    scope_discover,
    scope_gather,
    scope_tenant_slug,
)
from nimbusware_maker.session_scope import (
    approve_scope_pending,
    get_scope_pending,
    publish_scope_pending,
)

from nimbusware_compute.node_store import build_compute_node_store, default_tenant_id, row_to_public
from nimbusware_iam.context import resolve_store_tenant_id
router = APIRouter(tags=["maker"])


def _require_scope_writer(
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    session_id: UUID,
    actor: UUID,
) -> None:
    if nimbusware_collab_enabled():
        participants = collab_store.list_participants(session_id)
        if participants:
            require_session_participant(
                collab_store,
                session_id=session_id,
                user_id=actor,
                minimum_role="session_write",
            )
            return
    session = chat_store.get_session(session_id)
    host = getattr(session, "host_user_id", None) if session else None
    if host is None or host == actor:
        return
    raise HTTPException(
        status_code=403,
        detail=problem("forbidden", "session write access required"),
    )


def _require_scope_reader(
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    session_id: UUID,
    actor: UUID,
) -> None:
    if nimbusware_collab_enabled():
        participants = collab_store.list_participants(session_id)
        if participants:
            require_session_participant(
                collab_store,
                session_id=session_id,
                user_id=actor,
                minimum_role="session_read",
            )
            return
    pending = get_scope_pending(chat_store, session_id)
    if pending is not None:
        return
    raise HTTPException(
        status_code=403,
        detail=problem("forbidden", "scope review access required"),
    )


class ScopePublishBody(BaseModel):
    state: dict[str, Any]


class ScopePendingResponse(BaseModel):
    session_id: str
    scope_pending: dict[str, Any] | None = None
    scope_approved: dict[str, Any] | None = None


def _scope_pending_response(
    session_id: UUID,
    *,
    scope_pending: dict[str, Any] | None = None,
    scope_approved: dict[str, Any] | None = None,
    session: Any | None = None,
) -> ScopePendingResponse:
    if session is not None:
        meta = dict(session.metadata or {})
        if scope_pending is None:
            raw = meta.get("scope_pending")
            scope_pending = raw if isinstance(raw, dict) else None
        if scope_approved is None:
            raw = meta.get("scope_approved")
            scope_approved = raw if isinstance(raw, dict) else None
    return ScopePendingResponse(
        session_id=str(session_id),
        scope_pending=scope_pending,
        scope_approved=scope_approved,
    )


@router.post(
    "/sessions/{session_id}/start",
    response_model=StartChatSessionResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def start_chat_session(
    session_id: UUID,
    body: StartChatSessionBody,
    chat_store: ChatStoreDep,
    orch: OrchDep,
    project_store: ProjectStoreDep,
    store: StoreDep,
    _user: UserDep,
) -> StartChatSessionResponse:
    session = session_or_404(chat_store, session_id)
    project_uuid = UUID(str(session.project_id))
    path = chat_store.get_active_path(session_id)
    try:
        work_type = resolve_work_type(body.work_type, session)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_request",
                "work_type must be one of quick, patch, slice, campaign, factory",
            ),
        ) from exc
    work_type_source = resolve_work_type_source(body.work_type_source, session)
    if body.work_type:
        session = chat_store.update_session(session_id, work_type_override=work_type.value)

    profile = resolve_workflow_profile(
        body=body,
        work_type=work_type,
        project_store=project_store,
        project_uuid=project_uuid,
        last_classification=session.last_classification,
    )

    last_user = next((t for t in reversed(path) if t.role == "user"), None)
    requirements = requirements_payload(
        body, last_user.text if last_user else None
    ) or requirements_from_path(path)
    if work_type in (WorkType.CAMPAIGN, WorkType.FACTORY) and requirements is None:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "requirements or prior chat message required"),
        )

    enforce_discovery_gate(requirements, workflow_profile=profile)

    path_attachments = last_user.payload.get("attachments") if last_user else None
    patch_context = (
        patch_context_payload(body, session.last_classification, path_attachments)
        if work_type == WorkType.PATCH
        else None
    )

    try:
        if work_type in (WorkType.CAMPAIGN, WorkType.FACTORY):
            started = start_campaign(
                orch=orch,
                project_store=project_store,
                store=store,
                project_uuid=project_uuid,
                workflow_profile=profile,
                work_type=work_type,
                work_type_source=work_type_source,
                requirements=requirements,
                body=body,
            )
        else:
            started = start_run(
                orch=orch,
                project_store=project_store,
                store=store,
                project_uuid=project_uuid,
                workflow_profile=profile,
                work_type=work_type,
                work_type_source=work_type_source,
                requirements=requirements,
                patch_context=patch_context,
                body=body,
            )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("workflow_not_found", str(exc)),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("registry_key_error", str(exc)),
        ) from exc

    run_uuid = UUID(started["run_id"]) if started.get("run_id") else None
    campaign_uuid = UUID(started["campaign_id"]) if started.get("campaign_id") else None
    replay_alignment = None
    if run_uuid is not None:
        replay_alignment = maybe_apply_chat_replay_alignment(
            store,
            run_uuid,
            body,
            session_turns=path,
        )
    session = chat_store.update_session(
        session_id,
        run_id=run_uuid,
        campaign_id=campaign_uuid,
    )
    status_text = f"Started {work_type.value} run ({profile})."
    try:
        run_turn = chat_store.append_turn(
            session_id,
            role="run_status",
            text=status_text,
            payload={
                "workflow_profile": profile,
                "work_type": work_type.value,
                "work_type_source": work_type_source,
            },
            work_type=work_type.value,
            work_type_source=work_type_source,
            run_id=run_uuid,
            campaign_id=campaign_uuid,
        )
    except (KeyError, ValueError) as exc:
        raise chat_http_error(exc) from exc

    return StartChatSessionResponse(
        session_id=str(session_id),
        work_type=work_type.value,
        workflow_profile=profile,
        run_id=started.get("run_id"),
        campaign_id=started.get("campaign_id"),
        dispatch_mode=started.get("dispatch_mode"),
        turn=run_turn.to_dict(),
        replay_alignment=replay_alignment,
    )


@router.post(
    "/sessions/{session_id}/scope/publish",
    response_model=ScopePendingResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def post_session_scope_publish(
    session_id: UUID,
    body: ScopePublishBody,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    request: Request,
    user: OptionalUserDep,
) -> ScopePendingResponse:
    session_or_404(chat_store, session_id)
    _, actor = collab_session_actor(chat_store, session_id, request, user)
    _require_scope_writer(chat_store, collab_store, session_id, actor)
    try:
        publish_scope_pending(chat_store, session_id, body.state)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=problem("session_not_found", str(exc)),
        ) from exc
    session = chat_store.get_session(session_id)
    return _scope_pending_response(session_id, session=session)


@router.get(
    "/sessions/{session_id}/scope/pending",
    response_model=ScopePendingResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_session_scope_pending(
    session_id: UUID,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    request: Request,
    user: OptionalUserDep,
) -> ScopePendingResponse:
    session_or_404(chat_store, session_id)
    _, actor = collab_session_actor(chat_store, session_id, request, user)
    _require_scope_reader(chat_store, collab_store, session_id, actor)
    pending = get_scope_pending(chat_store, session_id)
    session = chat_store.get_session(session_id)
    approved = None
    if session is not None:
        raw = dict(session.metadata or {}).get("scope_approved")
        approved = raw if isinstance(raw, dict) else None
    return _scope_pending_response(session_id, scope_pending=pending, scope_approved=approved)


@router.post(
    "/sessions/{session_id}/scope/approve",
    response_model=ScopePendingResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def post_session_scope_approve(
    session_id: UUID,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    user: AuthUserDep,
) -> ScopePendingResponse:
    session_or_404(chat_store, session_id)
    _require_scope_reader(chat_store, collab_store, session_id, user.user_id)
    try:
        confirmed = approve_scope_pending(
            chat_store,
            session_id,
            actor_user_id=str(user.user_id),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=problem("session_not_found", str(exc)),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("scope_not_pending", str(exc)),
        ) from exc
    return _scope_pending_response(session_id, scope_pending=None, scope_approved=confirmed)


class ScopeDiscoverBody(BaseModel):
    business_prompt: str = Field(min_length=1, max_length=8000)


class ScopeAnswerBody(BaseModel):
    question_id: str = Field(default="", max_length=80)
    question: str = Field(default="", max_length=500)
    answer: str = Field(default="", max_length=4000)


class ScopeGatherBody(BaseModel):
    state: dict[str, Any]
    answers: list[ScopeAnswerBody] = Field(default_factory=list, max_length=10)
    recommend_for_me: bool = False
    archetype: str | None = Field(default=None, max_length=80)
    trust_score: float | None = Field(default=None, ge=0.0, le=10.0)


class ScopeDiscoverResponse(BaseModel):
    scope: dict[str, Any]


@router.post("/scope/discover", response_model=ScopeDiscoverResponse)
def post_scope_discover(body: ScopeDiscoverBody) -> ScopeDiscoverResponse:
    return ScopeDiscoverResponse(scope=scope_discover(body.business_prompt))


@router.post("/scope/gather", response_model=ScopeDiscoverResponse)
def post_scope_gather(body: ScopeGatherBody) -> ScopeDiscoverResponse:
    setup_bundle = env_str("NIMBUSWARE_SETUP_BUNDLE").strip() or "default"
    may_defer = autopilot_may_auto_defer(
        setup_bundle=setup_bundle,
        archetype=body.archetype,
        trust_score=body.trust_score,
    )
    recommend = body.recommend_for_me and may_defer
    gathered = scope_gather(
        body.state,
        [a.model_dump(mode="json") for a in body.answers],
        recommend_for_me_flag=recommend,
        tenant_slug=scope_tenant_slug(),
    )
    return ScopeDiscoverResponse(scope=enrich_scope_surface_bindings(gathered))


class ScopeRecommendBody(BaseModel):
    business_prompt: str = Field(min_length=1, max_length=8000)
    archetype: str | None = Field(default=None, max_length=80)


@router.post("/scope/recommend", response_model=ScopeDiscoverResponse)
def post_scope_recommend(body: ScopeRecommendBody) -> ScopeDiscoverResponse:
    setup_bundle = env_str("NIMBUSWARE_SETUP_BUNDLE").strip() or "default"
    tenant = scope_tenant_slug()
    state = scope_discover(body.business_prompt)
    recommended = recommend_for_me(state, tenant_slug=tenant)
    recommended["stack_manifest"] = manifest_for_archetype(
        setup_bundle=setup_bundle,
        archetype=body.archetype,
        tenant_slug=tenant,
    )
    return ScopeDiscoverResponse(
        scope=enrich_scope_surface_bindings(attach_discovery_summary(recommended)),
    )


class ScopeConfirmBody(BaseModel):
    state: dict[str, Any]


@router.post("/scope/confirm", response_model=ScopeDiscoverResponse)
def post_scope_confirm(body: ScopeConfirmBody) -> ScopeDiscoverResponse:
    try:
        confirmed = scope_confirm(body.state, tenant_slug=scope_tenant_slug())
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    return ScopeDiscoverResponse(scope=enrich_scope_surface_bindings(confirmed))

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

