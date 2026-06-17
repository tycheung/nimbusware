from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.access import assert_project_accessible
from nimbusware_api.deps import OrchDep, ProjectStoreDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.runs.create import PatchContextBody, RunRequirementsBody
from nimbusware_maker.intent import build_requirements_artifact
from nimbusware_maker.intent_classifier import WorkType
from nimbusware_maker.quick_mode import DEFAULT_QUICK_WORKFLOW
from nimbusware_orchestrator.patch_context import normalize_patch_context
from nimbusware_orchestrator.user_autopilot_profiles import apply_user_autopilot_at_run_start


class CreateChatSessionBody(BaseModel):
    project_id: str = Field(min_length=1, max_length=36)
    folder: str | None = Field(default=None, max_length=120)


class ChatMessageBody(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    attachments: list[dict[str, Any]] = Field(default_factory=list, max_length=8)


class AppendTurnBody(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    attachments: list[dict[str, Any]] = Field(default_factory=list, max_length=8)
    role: str = Field(default="user", max_length=32)


class ForkChatBody(BaseModel):
    turn_id: str = Field(min_length=36, max_length=36)


class ActiveLeafBody(BaseModel):
    leaf_turn_id: str = Field(min_length=36, max_length=36)


class SwitchModeBody(BaseModel):
    work_type: str = Field(min_length=1, max_length=32)
    rationale: str | None = Field(default=None, max_length=2000)
    align_run_replay: bool = False
    replay_from_seq: int | None = None


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
    align_run_replay: bool = False
    replay_from_seq: int | None = Field(default=None, ge=0)


class ChatSessionResponse(BaseModel):
    session_id: str
    project_id: str
    created_at: str
    updated_at: str | None = None
    title: str | None = None
    messages: list[dict[str, Any]]
    turns: list[dict[str, Any]] | None = None
    active_leaf_turn_id: str | None = None
    last_classification: dict[str, Any] | None = None
    work_type_override: str | None = None
    run_id: str | None = None
    campaign_id: str | None = None
    host_user_id: str | None = None
    workload_distribution: str | None = None
    metadata: dict[str, Any] | None = None
    participants: list[dict[str, Any]] | None = None
    my_participant_role: str | None = None


class ChatMessageResponse(BaseModel):
    message: dict[str, Any]
    classification: dict[str, Any]
    turn: dict[str, Any] | None = None


class ClassificationResponse(BaseModel):
    classification: dict[str, Any]


class StartChatSessionResponse(BaseModel):
    session_id: str
    work_type: str
    workflow_profile: str
    run_id: str | None = None
    campaign_id: str | None = None
    dispatch_mode: str | None = None
    turn: dict[str, Any] | None = None
    replay_alignment: dict[str, Any] | None = None


class ChatGraphResponse(BaseModel):
    session_id: str
    active_leaf_turn_id: str | None = None
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    branches: list[dict[str, Any]]


def project_metadata(project_store: ProjectStoreDep, project_uuid: UUID) -> dict[str, Any]:
    record = project_store.get(project_uuid)
    if record is None:
        raise HTTPException(
            status_code=422,
            detail=problem("project_not_found", f"Unknown project id: {project_uuid}"),
        )
    assert_project_accessible(record)
    data = record.to_dict()
    return {
        "project_id": data.get("project_id"),
        "name": data.get("name"),
        "template": data.get("template"),
        "default_workflow_profile": data.get("default_workflow_profile"),
        "default_work_type": data.get("default_work_type"),
    }


def requirements_payload(
    body: StartChatSessionBody, path_text: str | None
) -> dict[str, Any] | None:
    if body.requirements is not None:
        return build_requirements_artifact(
            business_prompt=body.requirements.business_prompt,
            clarifications=[c.model_dump(mode="json") for c in body.requirements.clarifications],
        )
    if path_text and path_text.strip():
        return build_requirements_artifact(business_prompt=path_text.strip())
    return None


def patch_context_payload(
    body: StartChatSessionBody,
    session_classification: dict[str, Any] | None,
    path_attachments: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    if body.patch_context is not None:
        return normalize_patch_context(
            body.patch_context.model_dump(mode="json", exclude_none=True)
        )
    extracted = (session_classification or {}).get("attachments_extracted")
    if extracted:
        return normalize_patch_context(extracted)
    if path_attachments:
        return normalize_patch_context(path_attachments[0])
    return None


def start_campaign(
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


def start_run(
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


def maybe_apply_chat_replay_alignment(
    store: Any,
    run_id: UUID,
    body: StartChatSessionBody,
    session_turns: list[Any] | None = None,
) -> dict[str, Any] | None:
    seq = body.replay_from_seq
    align = body.align_run_replay
    if seq is None and session_turns:
        for turn in reversed(session_turns):
            role = getattr(turn, "role", None) or (
                turn.get("role") if isinstance(turn, dict) else None
            )
            if role != "work_type_switch":
                continue
            payload = (
                getattr(turn, "payload", None)
                if not isinstance(turn, dict)
                else turn.get("payload")
            )
            block = dict(payload) if isinstance(payload, dict) else {}
            if block.get("align_run_replay") and block.get("replay_from_seq") is not None:
                seq = int(block["replay_from_seq"])
                align = True
            break
    if not align or seq is None:
        return None
    from nimbusware_orchestrator.replay_from import ReplayPolicy, emit_replay_started_event

    emit_replay_started_event(
        store,
        run_id=run_id,
        from_store_seq=int(seq),
        replay_policy=ReplayPolicy(),
        operator_ack=True,
        reason="chat_start_replay_alignment",
    )
    return {"from_store_seq": int(seq), "replay_started": True}


def resolve_workflow_profile(
    *,
    body: StartChatSessionBody,
    work_type: WorkType,
    project_store: ProjectStoreDep,
    project_uuid: UUID,
    last_classification: dict[str, Any] | None,
) -> str:
    profile = (body.workflow_profile or "").strip()
    if profile:
        return profile
    if last_classification:
        profile = str(last_classification.get("suggested_profile") or "").strip()
    if profile:
        return profile
    if work_type == WorkType.QUICK:
        return DEFAULT_QUICK_WORKFLOW
    if work_type in (WorkType.CAMPAIGN, WorkType.FACTORY):
        return (
            "campaign_factory_zero_touch"
            if work_type == WorkType.FACTORY
            else "campaign_micro_slice"
        )
    meta = project_metadata(project_store, project_uuid)
    return str(meta.get("default_workflow_profile") or "micro_slice")
