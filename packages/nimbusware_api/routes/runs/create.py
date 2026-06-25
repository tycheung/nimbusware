from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Header, HTTPException
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

from nimbusware_api.access import assert_project_accessible
from nimbusware_api.deps import OrchDep, ProjectStoreDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import (
    CREATE_RUN_RESPONSE_200,
    CREATE_RUN_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)
from nimbusware_env.settings_catalog import SettingScope
from nimbusware_env.settings_store import validate_patch
from nimbusware_maker.intent import build_requirements_artifact
from nimbusware_orchestrator.default_workflow_profile import default_workflow_profile
from nimbusware_orchestrator.user_autopilot_profiles import apply_user_autopilot_at_run_start
from nimbusware_orchestrator.user_enforcement_profiles import apply_user_enforcement_at_run_start

router = APIRouter()


class ClarificationAnswerBody(BaseModel):
    question_id: str = Field(default="", max_length=80)
    question: str = Field(default="", max_length=500)
    answer: str = Field(default="", max_length=4000)


class RunRequirementsBody(BaseModel):
    business_prompt: str = Field(min_length=1, max_length=8000)
    clarifications: list[ClarificationAnswerBody] = Field(default_factory=list, max_length=10)


class PatchContextBody(BaseModel):
    target_paths: list[str] = Field(default_factory=list, max_length=8)
    failing_test: str | None = Field(default=None, max_length=500)
    stack_trace: str | None = Field(default=None, max_length=4000)
    error_snippet: str | None = Field(default=None, max_length=2000)


class CreateRunBody(BaseModel):
    workflow_profile: str = Field(default_factory=default_workflow_profile, min_length=1)
    work_type: str | None = Field(default=None, max_length=32)
    work_type_source: str | None = Field(default=None, max_length=32)
    patch_context: PatchContextBody | None = None
    business_area_persona_id: str | None = Field(default=None, max_length=200)
    development_role_persona_id: str | None = Field(default=None, max_length=200)
    custom_agent_id: str | None = Field(default=None, max_length=120)
    memory_retrieval_enabled: bool | None = Field(default=None)
    memory_index_contribution: bool | None = Field(default=None)
    operator_settings: dict[str, str] | None = Field(
        default=None,
        description="Per-run operator overrides (run-scoped catalog keys only).",
    )
    project_id: str | None = Field(default=None, max_length=36)
    requirements: RunRequirementsBody | None = None
    autopilot_profile_id: str | None = Field(
        default=None,
        max_length=120,
        description="Saved operator autopilot profile to apply at run start",
    )
    enforcement_profile_id: str | None = Field(
        default=None,
        max_length=120,
        description="Saved operator enforcement profile to apply at run start",
    )
    consumer_archetype: str | None = Field(default=None, max_length=64)


@router.post(
    "/runs",
    responses={
        200: CREATE_RUN_RESPONSE_200,
        422: CREATE_RUN_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def create_run(
    body: CreateRunBody,
    orch: OrchDep,
    project_store: ProjectStoreDep,
    store: StoreDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    key_uuid: UUID | None = None
    if idempotency_key is not None and str(idempotency_key).strip():
        try:
            key_uuid = UUID(str(idempotency_key).strip())
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=problem(
                    "invalid_request",
                    "Idempotency-Key must be a UUID when set",
                    details={"header": "Idempotency-Key"},
                ),
            ) from exc
    try:
        memory_overrides: dict[str, bool] = {}
        if body.memory_retrieval_enabled is not None:
            memory_overrides["retrieval_enabled"] = body.memory_retrieval_enabled
        if body.memory_index_contribution is not None:
            memory_overrides["index_contribution"] = body.memory_index_contribution
        run_policy_overrides: dict[str, Any] | None = None
        if memory_overrides:
            run_policy_overrides = {"memory": memory_overrides}
        if body.consumer_archetype and str(body.consumer_archetype).strip():
            if run_policy_overrides is None:
                run_policy_overrides = {}
            run_policy_overrides["consumer_archetype"] = str(body.consumer_archetype).strip()
        if body.operator_settings:
            try:
                op = validate_patch(
                    body.operator_settings,
                    scope=SettingScope.RUN,
                    admin=False,
                )
            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=problem("invalid_request", str(exc)),
                ) from exc
            if run_policy_overrides is None:
                run_policy_overrides = {}
            run_policy_overrides["operator_settings"] = op
        project_uuid: UUID | None = None
        project = None
        if body.project_id is not None and str(body.project_id).strip():
            try:
                project_uuid = UUID(str(body.project_id).strip())
            except ValueError as exc:
                raise HTTPException(
                    status_code=422,
                    detail=problem("invalid_request", "project_id must be a UUID"),
                ) from exc
            project = project_store.get(project_uuid)
            if project is None:
                raise HTTPException(
                    status_code=422,
                    detail=problem("project_not_found", f"Unknown project id: {project_uuid}"),
                )
            assert_project_accessible(project)
        patch_ctx = (
            body.patch_context.model_dump(mode="json", exclude_none=True)
            if body.patch_context is not None
            else None
        )
        run_id = orch.create_run(
            body.workflow_profile,
            idempotency_key=key_uuid,
            correlation_id=key_uuid,
            business_area_persona_id=body.business_area_persona_id,
            development_role_persona_id=body.development_role_persona_id,
            custom_agent_id=body.custom_agent_id,
            run_policy_overrides=run_policy_overrides,
            project_id=project_uuid,
            project_name=project.name if project is not None else None,
            project_workspace_path=project.workspace_path if project is not None else None,
            project_template=project.template if project is not None else None,
            requirements=(
                build_requirements_artifact(
                    business_prompt=body.requirements.business_prompt,
                    clarifications=[
                        c.model_dump(mode="json") for c in body.requirements.clarifications
                    ],
                )
                if body.requirements is not None
                else None
            ),
            patch_context=patch_ctx,
            work_type=body.work_type,
            work_type_source=body.work_type_source,
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
    if body.enforcement_profile_id and str(body.enforcement_profile_id).strip():
        applied_enf = apply_user_enforcement_at_run_start(
            store,
            run_id,
            str(body.enforcement_profile_id),
            repo_root=orch.repo_root,
        )
        if applied_enf is None:
            raise HTTPException(
                status_code=422,
                detail=problem(
                    "enforcement_profile_not_found",
                    "Unknown enforcement profile id",
                    details={"profile_id": body.enforcement_profile_id},
                ),
            )
    return {"run_id": str(run_id)}
