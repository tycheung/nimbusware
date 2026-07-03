from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.access import assert_project_accessible
from api.deps import OrchDep, ProjectStoreDep, StoreDep
from api.errors import problem
from api.routes.runs.create import (
    RunRequirementsBody,
    build_requirements_from_body,
    enforce_discovery_gate,
)
from orchestrator.user_autopilot_profiles import apply_user_autopilot_at_run_start
from orchestrator.user_enforcement_profiles import apply_user_enforcement_at_run_start

router = APIRouter()


class CreateCampaignBody(BaseModel):
    project_id: str = Field(min_length=1, max_length=36)
    requirements: RunRequirementsBody
    autonomous: bool = True
    workflow_profile: str = Field(default="campaign_fullstack", min_length=1)
    autopilot_profile_id: str | None = Field(default=None, max_length=120)
    enforcement_profile_id: str | None = Field(default=None, max_length=120)


@router.post("/campaigns")
def create_campaign(
    body: CreateCampaignBody,
    orch: OrchDep,
    project_store: ProjectStoreDep,
    store: StoreDep,
) -> dict[str, Any]:
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
    requirements = build_requirements_from_body(body.requirements)
    enforce_discovery_gate(requirements, workflow_profile=body.workflow_profile)
    if orch.active_campaigns_for_project(str(project_uuid)) >= 1:
        raise HTTPException(
            status_code=429,
            detail=problem(
                "campaign_rate_limited",
                "one active campaign per project (safety policy)",
            ),
        )
    try:
        run_id = orch.create_run(
            body.workflow_profile,
            project_id=project_uuid,
            project_name=project.name,
            project_workspace_path=project.workspace_path,
            project_template=project.template,
            requirements=requirements,
            autonomous=body.autonomous,
        )
        ws = None
        if project.workspace_path:
            from pathlib import Path

            ws = Path(project.workspace_path)
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
        mode = orch.start_campaign(run_id, workspace=ws, autonomous=body.autonomous)
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
    return {
        "campaign_id": str(run_id),
        "run_id": str(run_id),
        "dispatch_mode": mode,
        "autonomous": body.autonomous,
        "workflow_profile": body.workflow_profile,
    }
