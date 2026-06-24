from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from nimbusware_api.deps import ChatStoreDep, OrchDep, ProjectStoreDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.chat_common import (
    StartChatSessionBody,
    StartChatSessionResponse,
    chat_http_error,
    maybe_apply_chat_replay_alignment,
    patch_context_payload,
    requirements_payload,
    resolve_workflow_profile,
    session_or_404,
    start_campaign,
    start_run,
)
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_api.user import UserDep
from nimbusware_maker.chat_service import (
    requirements_from_path,
    resolve_work_type,
    resolve_work_type_source,
)
from nimbusware_maker.intent_classifier import WorkType

router = APIRouter(tags=["maker"])


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
