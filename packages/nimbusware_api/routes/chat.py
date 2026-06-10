from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from nimbusware_api.deps import ChatStoreDep, OrchDep, ProjectStoreDep, StoreDep
from nimbusware_api.errors import problem
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
    StartChatSessionBody,
    StartChatSessionResponse,
    SwitchModeBody,
    patch_context_payload,
    project_metadata,
    requirements_payload,
    resolve_workflow_profile,
    start_campaign,
    start_run,
)
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_api.user import UserDep
from nimbusware_maker.chat_models import ChatSessionRecord
from nimbusware_maker.chat_service import (
    classification_dict,
    requirements_from_path,
    resolve_work_type,
    resolve_work_type_source,
    session_response,
    switch_mode_rationale,
)
from nimbusware_maker.intent_classifier import WorkType, classify_intent
from nimbusware_maker.quick_mode import quick_mode_enabled

router = APIRouter(prefix="/chat", tags=["maker"])


def _platform_hints(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    hints = dict(extra or {})
    hints.setdefault("quick_mode", quick_mode_enabled())
    return hints


def _session_or_404(chat_store: ChatStoreDep, session_id: UUID) -> ChatSessionRecord:
    session = chat_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "chat_session_not_found",
                "Unknown chat session",
                details={"session_id": str(session_id)},
            ),
        )
    return session


def _chat_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, KeyError):
        code = str(exc.args[0]) if exc.args else "not_found"
        if code == "chat_turn_not_found":
            return HTTPException(
                status_code=404,
                detail=problem(code, "Unknown chat turn"),
            )
        return HTTPException(
            status_code=404,
            detail=problem("chat_session_not_found", "Unknown chat session"),
        )
    if isinstance(exc, ValueError):
        return HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        )
    raise exc


@router.post("/sessions", response_model=ChatSessionResponse)
def create_chat_session(
    body: CreateChatSessionBody,
    chat_store: ChatStoreDep,
    project_store: ProjectStoreDep,
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
    session = chat_store.create_session(project_id=project_uuid)
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
    chat_store: ChatStoreDep,
    _user: UserDep,
    include_turns: bool = Query(default=False),
) -> ChatSessionResponse:
    session = _session_or_404(chat_store, session_id)
    return ChatSessionResponse(**session_response(chat_store, session, include_turns=include_turns))


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
    chat_store: ChatStoreDep,
    project_store: ProjectStoreDep,
    _user: UserDep,
) -> ChatMessageResponse:
    session = _session_or_404(chat_store, session_id)
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
    chat_store: ChatStoreDep,
    project_store: ProjectStoreDep,
    _user: UserDep,
) -> ChatMessageResponse:
    return append_chat_turn(
        session_id,
        AppendTurnBody(text=body.text, attachments=body.attachments),
        chat_store,
        project_store,
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
        if body.align_run_replay and body.replay_from_seq is not None:
            payload["replay_from_seq"] = body.replay_from_seq
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
    session = _session_or_404(chat_store, session_id)
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
        raise _chat_http_error(exc) from exc

    return StartChatSessionResponse(
        session_id=str(session_id),
        work_type=work_type.value,
        workflow_profile=profile,
        run_id=started.get("run_id"),
        campaign_id=started.get("campaign_id"),
        dispatch_mode=started.get("dispatch_mode"),
        turn=run_turn.to_dict(),
    )
