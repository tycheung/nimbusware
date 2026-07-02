from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from nimbusware_api.deps import ChatStoreDep, CollabStoreDep, OrchDep, ProjectStoreDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.auth import AuthUserDep, OptionalUserDep
from nimbusware_api.routes.chat_common import (
    StartChatSessionBody,
    StartChatSessionResponse,
    actor_user_id,
    chat_http_error,
    maybe_apply_chat_replay_alignment,
    patch_context_payload,
    requirements_payload,
    resolve_workflow_profile,
    session_or_404,
    start_campaign,
    start_run,
)
from nimbusware_api.routes.runs.create import enforce_discovery_gate
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_api.user import UserDep
from nimbusware_auth.permissions import require_session_participant
from nimbusware_env.env_flags import env_str, nimbusware_collab_enabled
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
    actor = actor_user_id(request, user)
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
    actor = actor_user_id(request, user)
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
