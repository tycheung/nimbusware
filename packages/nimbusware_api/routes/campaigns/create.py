"""POST /campaigns — create autonomous campaign run."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.access import assert_project_accessible
from nimbusware_api.deps import OrchDep, ProjectStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.runs.create import RunRequirementsBody
from nimbusware_maker.intent import build_requirements_artifact

router = APIRouter()


class CreateCampaignBody(BaseModel):
    project_id: str = Field(min_length=1, max_length=36)
    requirements: RunRequirementsBody
    autonomous: bool = True
    workflow_profile: str = Field(default="campaign_micro_slice", min_length=1)


@router.post("/campaigns")
def create_campaign(
    body: CreateCampaignBody,
    orch: OrchDep,
    project_store: ProjectStoreDep,
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
    from nimbusware_orchestrator.campaign_safety import active_campaigns_for_project

    if active_campaigns_for_project(orch._store, str(project_uuid)) >= 1:
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
            requirements=build_requirements_artifact(
                business_prompt=body.requirements.business_prompt,
                clarifications=[c.model_dump(mode="json") for c in body.requirements.clarifications],
            ),
            autonomous=body.autonomous,
        )
        ws = None
        if project.workspace_path:
            from pathlib import Path

            ws = Path(project.workspace_path)
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
