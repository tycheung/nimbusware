from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_orchestrator.autopilot_profiles import (
    autopilot_profile_from_rows,
    set_run_autopilot_override,
)

router = APIRouter()


class RunAutopilotBody(BaseModel):
    level: int = Field(ge=0, le=10, default=5)
    checkpoints: list[str] | None = None


class RunAutopilotResponse(BaseModel):
    run_id: str
    level: int
    name: str
    checkpoints: list[str] = Field(default_factory=list)
    custom: bool = False


@router.get(
    "/runs/{run_id}/autopilot",
    response_model=RunAutopilotResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_run_autopilot(run_id: UUID, store: StoreDep) -> RunAutopilotResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    profile = autopilot_profile_from_rows(rows)
    return RunAutopilotResponse(
        run_id=str(run_id),
        level=profile.level,
        name=profile.name,
        checkpoints=sorted(profile.checkpoints),
        custom=profile.custom,
    )


@router.put(
    "/runs/{run_id}/autopilot",
    response_model=RunAutopilotResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def put_run_autopilot(
    run_id: UUID,
    body: RunAutopilotBody,
    store: StoreDep,
) -> RunAutopilotResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    custom = set(body.checkpoints) if body.checkpoints else None
    profile = set_run_autopilot_override(str(run_id), level=body.level, checkpoints=custom)
    return RunAutopilotResponse(
        run_id=str(run_id),
        level=profile.level,
        name=profile.name,
        checkpoints=sorted(profile.checkpoints),
        custom=profile.custom,
    )
