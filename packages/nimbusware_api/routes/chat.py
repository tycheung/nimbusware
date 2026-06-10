from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.access import assert_project_accessible
from nimbusware_api.deps import OrchDep, ProjectStoreDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.runs.create import PatchContextBody, RunRequirementsBody
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_api.user import UserDep
from nimbusware_maker.intent import build_requirements_artifact
from nimbusware_maker.intent_classifier import (
    ClassificationResult,
    WorkType,
    classify_intent,
)
from nimbusware_maker.quick_mode import DEFAULT_QUICK_WORKFLOW, quick_mode_enabled
from nimbusware_orchestrator.patch_context import normalize_patch_context
from nimbusware_orchestrator.user_autopilot_profiles import apply_user_autopilot_at_run_start

router = APIRouter(prefix="/chat", tags=["maker"])


@dataclass
class ChatSession:
    session_id: str
    project_id: str
    created_at: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    last_classification: dict[str, Any] | None = None
    work_type_override: str | None = None
    run_id: str | None = None
    campaign_id: str | None = None


_chat_sessions: dict[str, ChatSession] = {}


class CreateChatSessionBody(BaseModel):
    project_id: str = Field(min_length=1, max_length=36)


class ChatMessageBody(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    attachments: list[dict[str, Any]] = Field(default_factory=list, max_length=8)


class ClassifyIntentBody(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    attachments: list[dict[str, Any]] = Field(default_factory=list, max_length=8)
    project_id: str | None = Field(default=None, max_length=36)
    platform_hints: dict[str, Any] = Field(default_factory=dict)


class StartChatSessionBody(BaseModel):
    work_type: str | None = Field(default=None, max_length=32)
    work_type_source: str | None = Field(default=None, max_length=32)
    workflow_profile: str | None = Field(default=None, max_length=120)
    requirements: RunRequirementsBody | None = None
    patch_context: PatchContextBody | None = None
    autopilot_profile_id: str | None = Field(default=None, max_length=120)
    autonomous: bool = True


class ChatSessionResponse(BaseModel):
    session_id: str
    project_id: str
    created_at: str
    messages: list[dict[str, Any]]
    last_classification: dict[str, Any] | None = None
    work_type_override: str | None = None
    run_id: str | None = None
    campaign_id: str | None = None


class ChatMessageResponse(BaseModel):
    message: dict[str, Any]
    classification: dict[str, Any]


class ClassificationResponse(BaseModel):
    classification: dict[str, Any]


class StartChatSessionResponse(BaseModel):
    session_id: str
    work_type: str
    workflow_profile: str
    run_id: str | None = None
    campaign_id: str | None = None
    dispatch_mode: str | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_or_404(session_id: str) -> ChatSession:
    state = _chat_sessions.get(session_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "chat_session_not_found",
                "Unknown chat session",
                details={"session_id": session_id},
            ),
        )
    return state


def _project_metadata(project_store: ProjectStoreDep, project_uuid: UUID) -> dict[str, Any]:
    record = project_store.get(project_uuid)
    if record is None:
        raise HTTPException(
            status_code=422,
            detail=problem("project_not_found", f"Unknown project id: {project_uuid}"),
        )
    assert_project_accessible(record)
    data = record.to_dict()  # type: ignore[attr-defined]
    return {
        "project_id": data.get("project_id"),
        "name": data.get("name"),
        "template": data.get("template"),
        "default_workflow_profile": data.get("default_workflow_profile"),
        "default_work_type": data.get("default_work_type"),
    }


def _platform_hints(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    hints = dict(extra or {})
    hints.setdefault("quick_mode", quick_mode_enabled())
    return hints


def _classification_dict(result: ClassificationResult) -> dict[str, Any]:
    return result.to_dict()


def _requirements_payload(
    body: StartChatSessionBody, session: ChatSession
) -> dict[str, Any] | None:
    if body.requirements is not None:
        return build_requirements_artifact(
            business_prompt=body.requirements.business_prompt,
            clarifications=[c.model_dump(mode="json") for c in body.requirements.clarifications],
        )
    for msg in reversed(session.messages):
        if msg.get("role") == "user" and str(msg.get("text") or "").strip():
            return build_requirements_artifact(business_prompt=str(msg["text"]))
    return None


def _patch_context_payload(
    body: StartChatSessionBody,
    session: ChatSession,
) -> dict[str, Any] | None:
    if body.patch_context is not None:
        return normalize_patch_context(
            body.patch_context.model_dump(mode="json", exclude_none=True)
        )
    extracted = (session.last_classification or {}).get("attachments_extracted")
    return normalize_patch_context(extracted)


def _resolve_work_type_source(body: StartChatSessionBody, session: ChatSession) -> str:
    raw = (body.work_type_source or "").strip().lower()
    if raw in {"classifier", "operator_override", "ide"}:
        return raw
    if body.work_type or session.work_type_override:
        return "operator_override"
    return "classifier"


def _resolve_work_type(body: StartChatSessionBody, session: ChatSession) -> WorkType:
    raw = (body.work_type or session.work_type_override or "").strip().lower()
    if not raw and session.last_classification:
        raw = str(session.last_classification.get("work_type") or "").strip().lower()
    try:
        return WorkType(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_request",
                "work_type must be one of quick, patch, slice, campaign, factory",
            ),
        ) from exc


def _start_campaign(
    *,
    orch: OrchDep,
    project_store: ProjectStoreDep,
    store: StoreDep,
    project_uuid: UUID,
    workflow_profile: str,
    work_type: WorkType,
    work_type_source: str,
    requirements: dict[str, Any] | None,
    body: StartChatSessionBody,
) -> dict[str, Any]:
    project = project_store.get(project_uuid)
    if project is None:
        raise HTTPException(
            status_code=422,
            detail=problem("project_not_found", f"Unknown project id: {project_uuid}"),
        )
    if orch.active_campaigns_for_project(str(project_uuid)) >= 1:
        raise HTTPException(
            status_code=429,
            detail=problem(
                "campaign_rate_limited",
                "one active campaign per project (safety policy)",
            ),
        )
    run_id = orch.create_run(
        workflow_profile,
        project_id=project_uuid,
        project_name=project.name,
        project_workspace_path=project.workspace_path,
        project_template=project.template,
        requirements=requirements,
        autonomous=body.autonomous,
        work_type=work_type.value,
        work_type_source=work_type_source,
    )
    ws = Path(project.workspace_path) if project.workspace_path else None
    if body.autopilot_profile_id and str(body.autopilot_profile_id).strip():
        applied = apply_user_autopilot_at_run_start(
            store,
            run_id,
            str(body.autopilot_profile_id),
            repo_root=orch.repo_root,
        )
        if applied is None:
            raise HTTPException(
                status_code=422,
                detail=problem(
                    "autopilot_profile_not_found",
                    "Unknown autopilot profile id",
                    details={"profile_id": body.autopilot_profile_id},
                ),
            )
    mode = orch.start_campaign(run_id, workspace=ws, autonomous=body.autonomous)
    return {
        "run_id": str(run_id),
        "campaign_id": str(run_id),
        "dispatch_mode": mode,
    }


def _start_run(
    *,
    orch: OrchDep,
    project_store: ProjectStoreDep,
    store: StoreDep,
    project_uuid: UUID,
    workflow_profile: str,
    work_type: WorkType,
    work_type_source: str,
    requirements: dict[str, Any] | None,
    patch_context: dict[str, Any] | None,
    body: StartChatSessionBody,
) -> dict[str, Any]:
    project = project_store.get(project_uuid)
    if project is None:
        raise HTTPException(
            status_code=422,
            detail=problem("project_not_found", f"Unknown project id: {project_uuid}"),
        )
    run_id = orch.create_run(
        workflow_profile,
        project_id=project_uuid,
        project_name=project.name,
        project_workspace_path=project.workspace_path,
        project_template=project.template,
        requirements=requirements,
        patch_context=patch_context,
        work_type=work_type.value,
        work_type_source=work_type_source,
    )
    if body.autopilot_profile_id and str(body.autopilot_profile_id).strip():
        applied = apply_user_autopilot_at_run_start(
            store,
            run_id,
            str(body.autopilot_profile_id),
            repo_root=orch.repo_root,
        )
        if applied is None:
            raise HTTPException(
                status_code=422,
                detail=problem(
                    "autopilot_profile_not_found",
                    "Unknown autopilot profile id",
                    details={"profile_id": body.autopilot_profile_id},
                ),
            )
    return {"run_id": str(run_id), "campaign_id": None, "dispatch_mode": None}


@router.post("/sessions", response_model=ChatSessionResponse)
def create_chat_session(
    body: CreateChatSessionBody,
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
    _project_metadata(project_store, project_uuid)
    session_id = str(uuid4())
    state = ChatSession(
        session_id=session_id,
        project_id=str(project_uuid),
        created_at=_utc_now(),
    )
    _chat_sessions[session_id] = state
    return ChatSessionResponse(
        session_id=state.session_id,
        project_id=state.project_id,
        created_at=state.created_at,
        messages=state.messages,
        last_classification=state.last_classification,
        work_type_override=state.work_type_override,
        run_id=state.run_id,
        campaign_id=state.campaign_id,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_chat_session(session_id: UUID, _user: UserDep) -> ChatSessionResponse:
    state = _session_or_404(str(session_id))
    return ChatSessionResponse(
        session_id=state.session_id,
        project_id=state.project_id,
        created_at=state.created_at,
        messages=state.messages,
        last_classification=state.last_classification,
        work_type_override=state.work_type_override,
        run_id=state.run_id,
        campaign_id=state.campaign_id,
    )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def post_chat_message(
    session_id: UUID,
    body: ChatMessageBody,
    project_store: ProjectStoreDep,
    _user: UserDep,
) -> ChatMessageResponse:
    state = _session_or_404(str(session_id))
    project_uuid = UUID(state.project_id)
    meta = _project_metadata(project_store, project_uuid)
    result = classify_intent(
        body.text,
        attachments=body.attachments,
        project_metadata=meta,
        platform_hints=_platform_hints(),
    )
    message = {
        "role": "user",
        "text": body.text,
        "attachments": body.attachments,
        "posted_at": _utc_now(),
    }
    state.messages.append(message)
    state.last_classification = _classification_dict(result)
    return ChatMessageResponse(
        message=message,
        classification=state.last_classification,
    )


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
        meta = _project_metadata(project_store, project_uuid)
    result = classify_intent(
        body.message,
        attachments=body.attachments,
        project_metadata=meta,
        platform_hints=_platform_hints(body.platform_hints),
    )
    return ClassificationResponse(classification=_classification_dict(result))


@router.post(
    "/sessions/{session_id}/start",
    response_model=StartChatSessionResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def start_chat_session(
    session_id: UUID,
    body: StartChatSessionBody,
    orch: OrchDep,
    project_store: ProjectStoreDep,
    store: StoreDep,
    _user: UserDep,
) -> StartChatSessionResponse:
    state = _session_or_404(str(session_id))
    project_uuid = UUID(state.project_id)
    work_type = _resolve_work_type(body, state)
    work_type_source = _resolve_work_type_source(body, state)
    if body.work_type:
        state.work_type_override = work_type.value

    profile = (body.workflow_profile or "").strip()
    if not profile:
        if state.last_classification:
            profile = str(state.last_classification.get("suggested_profile") or "").strip()
        if not profile:
            if work_type == WorkType.QUICK:
                profile = DEFAULT_QUICK_WORKFLOW
            elif work_type in (WorkType.CAMPAIGN, WorkType.FACTORY):
                profile = (
                    "campaign_factory_zero_touch"
                    if work_type == WorkType.FACTORY
                    else "campaign_micro_slice"
                )
            else:
                meta = _project_metadata(project_store, project_uuid)
                profile = str(meta.get("default_workflow_profile") or "micro_slice")

    requirements = _requirements_payload(body, state)
    if work_type in (WorkType.CAMPAIGN, WorkType.FACTORY) and requirements is None:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "requirements or prior chat message required"),
        )

    patch_context = _patch_context_payload(body, state) if work_type == WorkType.PATCH else None

    try:
        if work_type in (WorkType.CAMPAIGN, WorkType.FACTORY):
            started = _start_campaign(
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
            started = _start_run(
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

    state.run_id = started.get("run_id")
    state.campaign_id = started.get("campaign_id")
    return StartChatSessionResponse(
        session_id=state.session_id,
        work_type=work_type.value,
        workflow_profile=profile,
        run_id=state.run_id,
        campaign_id=state.campaign_id,
        dispatch_mode=started.get("dispatch_mode"),
    )
