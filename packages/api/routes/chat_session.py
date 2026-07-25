from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.deps import ChatStoreDep, CollabStoreDep, OrchDep, ProjectStoreDep, StoreDep
from api.errors import problem
from api.routes.auth import AuthUserDep, OptionalUserDep
from api.routes.chat_common import (
    StartChatSessionBody,
    StartChatSessionResponse,
    actor_user_id,
    chat_http_error,
    maybe_apply_chat_replay_alignment,
    patch_context_payload,
    require_collab_enabled,
    requirements_payload,
    resolve_workflow_profile,
    start_campaign,
    start_run,
)
from api.routes.chat_service import (
    collab_session_actor,
    session_or_404,
)
from api.routes.runs.create import enforce_discovery_gate
from api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from api.schemas.peel_responses import (
    compute_json_openapi_responses,
    llm_json_openapi_responses,
    with_long_tail_peel_503,
)
from api.user import UserDep
from auth.permissions import require_session_participant
from compute.node_store import build_compute_node_store, default_tenant_id, row_to_public
from env.env_flags import env_str, nimbusware_collab_enabled, nimbusware_database_url
from iam.context import resolve_store_tenant_id
from maker.archetype_surface_defaults import manifest_for_archetype
from maker.autopilot_defer_matrix import autopilot_may_auto_defer
from maker.chat.service import (
    requirements_from_path,
    resolve_work_type,
    resolve_work_type_source,
)
from maker.intent.classifier import WorkType
from maker.intent.scope_discovery import (
    attach_discovery_summary,
    enrich_scope_surface_bindings,
    recommend_for_me,
    scope_confirm,
    scope_discover,
    scope_gather,
    scope_tenant_slug,
)
from maker.session_scope import (
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
    responses=with_long_tail_peel_503(
        {404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
    ),  # sak512-i
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
                "work_type must be one of quick, patch, slice, campaign, factory, self_evolve",
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
    if work_type in (WorkType.CAMPAIGN, WorkType.FACTORY, WorkType.SELF_EVOLVE) and requirements is None:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "requirements or prior chat message required"),
        )
    if work_type == WorkType.SELF_EVOLVE and requirements is not None:
        from maker.intent.domain_keywords import attach_domain_keywords

        requirements = attach_domain_keywords(requirements) or requirements

    enforce_discovery_gate(requirements, workflow_profile=profile)

    path_attachments = last_user.payload.get("attachments") if last_user else None
    patch_context = (
        patch_context_payload(body, session.last_classification, path_attachments)
        if work_type == WorkType.PATCH
        else None
    )

    try:
        if work_type in (WorkType.CAMPAIGN, WorkType.FACTORY, WorkType.SELF_EVOLVE):
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
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak512-i
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
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak512-i
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
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak512-i
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


@router.post(
    "/scope/discover",
    response_model=ScopeDiscoverResponse,
    responses=llm_json_openapi_responses(),  # sak497-e
)
def post_scope_discover(body: ScopeDiscoverBody) -> ScopeDiscoverResponse:
    return ScopeDiscoverResponse(scope=scope_discover(body.business_prompt))


@router.post(
    "/scope/gather",
    response_model=ScopeDiscoverResponse,
    responses=llm_json_openapi_responses(),  # sak497-e
)
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


@router.post(
    "/scope/recommend",
    response_model=ScopeDiscoverResponse,
    responses=llm_json_openapi_responses(),  # sak497-e
)
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


@router.post(
    "/scope/confirm",
    response_model=ScopeDiscoverResponse,
    responses=llm_json_openapi_responses(),  # sak497-e
)
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


class DelegateControlResponse(BaseModel):
    """POST session compute delegate-control (`sak444-d`)."""

    session_id: str | None = None
    allow_host_resource_management: bool | None = None
    node: dict[str, Any] | None = None
    via: str | None = None
    status: str | None = None
    error: str | None = None
    feature: str | None = None


@router.post(
    "/sessions/{session_id}/compute/delegate-control",
    response_model=DelegateControlResponse,
    response_model_exclude_none=True,
    summary="Session compute delegate-control (broker-first; sak444-d)",
    responses=compute_json_openapi_responses(
        not_found=PROBLEM_RESPONSE_404,
    ),  # sak513-a
)
def session_compute_delegate_control(
    session_id: UUID,
    body: DelegateControlBody,
    request: Request,
    chat_store: ChatStoreDep,
    collab_store: CollabStoreDep,
    user: OptionalUserDep,
    _user: UserDep,
) -> dict[str, Any]:
    from broker_client.flags import broker_compute_enabled
    from broker_client.stage_bind.compute import (
        build_compute_list_nodes_payload,
        build_compute_register_payload,
        compute_node_via_broker,
        node_id_from_broker_record,
    )

    require_collab_enabled()
    session_or_404(chat_store, session_id)
    actor_id = user.user_id if user is not None else actor_user_id(request, user)
    require_session_participant(
        collab_store,
        session_id=session_id,
        user_id=actor_id,
        minimum_role="session_write",
    )

    if broker_compute_enabled():
        try:
            from compute.broker_session_status import assert_broker_compute_ok

            listed = assert_broker_compute_ok(
                compute_node_via_broker(
                    build_compute_list_nodes_payload(session_id=str(session_id))
                ),
                feature="delegate_control.list",
                list_key="nodes",
            )
            from compute.broker_node_match import pick_broker_node_for_user

            nodes = listed.get("nodes") if isinstance(listed, dict) else None
            target = None
            if isinstance(nodes, list):
                target = pick_broker_node_for_user(nodes, str(actor_id))
            if target is None:
                from compute.broker_route import map_broker_chat_compute_miss

                return map_broker_chat_compute_miss(
                    "no compute node for session",
                    feature="delegate_control",
                    only_msg=(
                        "register compute for this session before delegating control"
                    ),
                )
            nid = node_id_from_broker_record(target)
            caps = list(target.get("caps") or []) if isinstance(target.get("caps"), list) else []
            caps = [
                c
                for c in caps
                if not str(c).startswith("allow_host_resource_management=")
            ]
            caps.append(
                f"allow_host_resource_management="
                f"{'true' if body.allow_host_resource_management else 'false'}"
            )
            from compute.broker_session_status import assert_broker_compute_record_ok

            raw = assert_broker_compute_record_ok(
                compute_node_via_broker(
                    build_compute_register_payload(
                        str(target.get("label") or f"user:{actor_id}"),
                        caps=caps,
                        node_id=nid or None,
                        session_id=str(session_id),
                    )
                ),
                feature="delegate_control.register",
                record_key="node",
            )
            node = raw.get("node") if isinstance(raw.get("node"), dict) else raw
            return {
                "node": {
                    "node_id": node_id_from_broker_record(node),
                    "display_name": node.get("label"),
                    "session_id": str(session_id),
                    "allow_host_resource_management": body.allow_host_resource_management,
                    "via": "broker",
                }
            }
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            from compute.broker_route import map_broker_compute_http_error

            return map_broker_compute_http_error(
                exc,
                feature="delegate_control",
                only_msg=(
                    "session compute delegate-control unavailable under "
                    f"NIMBUSWARE_BROKER_COMPUTE=2: {exc}"
                ),
            )

    # sak447-i: COMPUTE peel already handled above — never fall through to node_store.
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


class SessionOptimizerWeightsResponse(BaseModel):
    """GET/PUT session optimizer-weights (`sak445-d`)."""

    priority: list[str] = Field(default_factory=list)
    weights: dict[str, Any] = Field(default_factory=dict)


@router.get(
    "/sessions/{session_id}/optimizer-weights",
    response_model=SessionOptimizerWeightsResponse,
    response_model_exclude_none=True,
    summary="Session optimizer weights (`sak445-d`)",
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak513-b
)
def get_session_optimizer_weights(
    session_id: UUID,
    chat_store: ChatStoreDep,
    _user: UserDep,
) -> dict[str, Any]:
    sess = session_or_404(chat_store, session_id)
    from maker.optimizer_weights_store import DEFAULT_OPTIMIZER_WEIGHTS
    from orchestrator.role_claims_mesh import optimizer_weights_from_session_metadata

    meta = sess.metadata if isinstance(sess.metadata, dict) else {}
    priority = meta.get("optimizer_priority")
    if not isinstance(priority, list):
        priority = list(DEFAULT_OPTIMIZER_WEIGHTS.keys())
    weights = optimizer_weights_from_session_metadata(meta)
    return {"priority": priority, "weights": weights}


@router.put(
    "/sessions/{session_id}/optimizer-weights",
    response_model=SessionOptimizerWeightsResponse,
    response_model_exclude_none=True,
    summary="Update session optimizer weights (`sak445-d`)",
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak513-b
)
def put_session_optimizer_weights(
    session_id: UUID,
    body: SessionOptimizerBody,
    chat_store: ChatStoreDep,
    _user: UserDep,
) -> dict[str, Any]:
    session_or_404(chat_store, session_id)
    from maker.optimizer_weights_store import DEFAULT_OPTIMIZER_WEIGHTS
    from orchestrator.collab.optimizer import weights_from_priority

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


class SessionComputeOptInResponse(BaseModel):
    """POST session compute opt-in/out (`sak443-g`)."""

    session_id: str | None = None
    enabled: bool | None = None
    share_policy: str | None = None
    via: str | None = None
    status: str | None = None
    feature: str | None = None
    error: str | None = None
    node: dict[str, Any] | None = None


@router.post(
    "/sessions/{session_id}/compute/opt-in",
    response_model=SessionComputeOptInResponse,
    response_model_exclude_none=True,
    summary="Session compute opt-in/out (broker-first; sak443-g)",
    responses=compute_json_openapi_responses(
        not_found=PROBLEM_RESPONSE_404,
    ),  # sak513-a
)
def session_compute_opt_in(
    session_id: UUID,
    body: SessionComputeOptInBody,
    request: Request,
    chat_store: ChatStoreDep,
    user: OptionalUserDep,
    _user: UserDep,
) -> dict[str, Any]:
    from broker_client.flags import broker_compute_enabled
    from broker_client.stage_bind.compute import (
        build_compute_register_payload,
        compute_node_via_broker,
        node_id_from_broker_record,
    )

    session_or_404(chat_store, session_id)
    actor_id = user.user_id if user is not None else None
    if actor_id is None and nimbusware_collab_enabled():
        actor_id = actor_user_id(request, user)

    if broker_compute_enabled() and body.enabled:
        try:
            label = body.host_label or (f"user:{actor_id}" if actor_id else "local")
            caps = ["mesh_worker", "session_opt_in"]
            if actor_id:
                caps.append(f"user:{actor_id}")
            from compute.broker_session_status import assert_broker_compute_record_ok

            raw = assert_broker_compute_record_ok(
                compute_node_via_broker(
                    build_compute_register_payload(
                        label,
                        caps=caps,
                        session_id=str(session_id),
                    )
                ),
                feature="session_compute_opt_in.register",
                record_key="node",
            )
            node = raw.get("node") if isinstance(raw.get("node"), dict) else raw
            nid = node_id_from_broker_record(node)
            return {
                "session_id": str(session_id),
                "enabled": True,
                "share_policy": body.share_policy,
                "via": "broker",
                "node": {
                    "node_id": nid,
                    "display_name": node.get("label"),
                    "host_label": node.get("label"),
                    "session_id": str(session_id),
                    "share_policy": body.share_policy,
                },
            }
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            from compute.broker_route import map_broker_compute_http_error

            return map_broker_compute_http_error(
                exc,
                feature="session_compute_opt_in",
                only_msg=(
                    "session compute opt-in unavailable under "
                    f"NIMBUSWARE_BROKER_COMPUTE=2: {exc}"
                ),
                miss_extra={
                    "session_id": str(session_id),
                    "enabled": True,
                    "share_policy": body.share_policy,
                },
            )

    # sak429-e / sak443-c: under COMPUTE dual-run, never fall through to node_store
    # (incl. opt-out). Opt-out is explicit broker_opt_out — not masquerading via=broker.
    if broker_compute_enabled():
        return {
            "session_id": str(session_id),
            "enabled": body.enabled,
            "share_policy": body.share_policy,
            "via": "broker_opt_out" if not body.enabled else "broker",
            "status": "ok",
            "feature": (
                "session_compute_opt_out" if not body.enabled else "session_compute_opt_in"
            ),
            "node": None,
        }

    from compute.broker_route import refuse_broker_only_http

    refuse_broker_only_http()
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


class SessionComputeStatusResponse(BaseModel):
    """GET session compute status (`sak441-e`)."""

    session_id: str | None = None
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    queue_depth: int = 0
    via: str | None = None
    status: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/sessions/{session_id}/compute/status",
    response_model=SessionComputeStatusResponse,
    response_model_exclude_none=True,
    summary="Session compute status (broker-first; sak431-g / sak435-e / sak441-e)",
    responses=compute_json_openapi_responses(
        not_found=PROBLEM_RESPONSE_404,
    ),
)
def session_compute_status(
    session_id: UUID,
    chat_store: ChatStoreDep,
    _user: UserDep,
) -> dict[str, Any]:
    """Broker-first session compute status (`sak431-g` / `sak435-d` / `sak436-b`)."""
    from broker_client.flags import broker_compute_enabled
    from compute.broker_route import map_broker_compute_http_error, refuse_broker_only_http
    from compute.broker_session_status import broker_session_compute_status

    session_or_404(chat_store, session_id)

    if broker_compute_enabled():
        try:
            raw = broker_session_compute_status(str(session_id))
            nodes_out = [
                {
                    "node_id": n.get("node_id"),
                    "display_name": n.get("display_name"),
                    "via": n.get("via", "broker"),
                }
                for n in (raw.get("nodes") or [])
                if isinstance(n, dict)
            ]
            out: dict[str, Any] = {
                "session_id": str(session_id),
                "nodes": nodes_out,
                "queue_depth": int(raw.get("queue_depth") or 0),
            }
            if raw.get("via") == "broker_miss" or raw.get("status") == "degraded":  # sak492-g
                out["via"] = raw.get("via", "broker_miss")
                out["status"] = raw.get("status", "degraded")
                if raw.get("error") is not None:
                    out["error"] = raw.get("error")
                if raw.get("feature") is not None:
                    out["feature"] = raw.get("feature")
                return out
            return {**out, "via": "broker", "status": "ok"}
        except Exception as exc:  # noqa: BLE001
            return map_broker_compute_http_error(
                exc,
                feature="session_compute_status",
                only_msg=f"session compute status unavailable: {exc}",
                miss_extra={
                    "session_id": str(session_id),
                    "nodes": [],
                    "queue_depth": 0,
                    "status": "degraded",
                },
            )

    refuse_broker_only_http()
    store = build_compute_node_store(nimbusware_database_url())
    from compute.work_unit import get_work_unit_queue

    rows = store.list_for_session(session_id)
    return {
        "session_id": str(session_id),
        "nodes": [row_to_public(r) for r in rows],
        "queue_depth": get_work_unit_queue().queued_count(session_id=session_id),
    }


class ParticipantRoleBindingBody(BaseModel):
    model_config = {"protected_namespaces": ()}

    agent_role: str = Field(min_length=1, max_length=128)
    provider_kind: str = Field(default="cloud", max_length=32)
    provider_id: str = Field(min_length=1, max_length=64)
    model_id: str = Field(min_length=1, max_length=256)
    connection_id: str | None = Field(default=None, max_length=128)


class ParticipantBindingsResponse(BaseModel):
    """GET/PUT session participant-bindings (`sak446-a`)."""

    user_id: str | None = None
    roles: dict[str, Any] = Field(default_factory=dict)


@router.get(
    "/sessions/{session_id}/participant-bindings",
    response_model=ParticipantBindingsResponse,
    response_model_exclude_none=True,
    summary="Participant model bindings (`sak446-a`)",
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak513-c
)
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
    from orchestrator.collab.binding_resolver import participant_binding_overrides

    return {
        "user_id": actor_id,
        "roles": participant_binding_overrides(meta, str(actor_id)),
    }


@router.put(
    "/sessions/{session_id}/participant-bindings",
    response_model=ParticipantBindingsResponse,
    response_model_exclude_none=True,
    summary="Update participant model binding (`sak446-a`)",
    responses=with_long_tail_peel_503({404: PROBLEM_RESPONSE_404}),  # sak513-c
)
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
    from orchestrator.collab.binding_resolver import (
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
