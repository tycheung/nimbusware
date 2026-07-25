from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import StoreDep
from api.errors import problem
from api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from api.schemas.peel_responses import runs_json_openapi_responses
from maker.workspace.workspace import resolve_run_workspace
from orchestrator.improvement.evolution_ledger import (
    evolution_timeline_from_rows,
    pending_proposals,
)
from orchestrator.improvement.prompt_evolution import promote_or_reject_prompt

router = APIRouter()


class EvolutionTimelineResponse(BaseModel):
    model_config = {"extra": "allow"}

    run_id: str | None = None
    timeline: list[dict[str, Any]] | None = None
    pending: list[dict[str, Any]] | None = None
    count: int | None = None


class EvolutionPromoteBody(BaseModel):
    artifact_id: str = Field(min_length=1)
    promote: bool = True


@router.get(
    "/runs/{run_id}/evolution",
    response_model=EvolutionTimelineResponse,
    response_model_exclude_none=True,
    summary="Evolution ledger timeline",
    responses={
        **runs_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),
        422: PROBLEM_RESPONSE_422,
    },
)
def get_run_evolution(run_id: UUID, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    timeline = evolution_timeline_from_rows(rows)
    return {
        "run_id": str(run_id),
        "timeline": timeline,
        "pending": pending_proposals(rows),
        "count": len(timeline),
    }


@router.post(
    "/runs/{run_id}/evolution/promote",
    response_model=EvolutionTimelineResponse,
    response_model_exclude_none=True,
    summary="Promote or reject a prompt evolution artifact",
    responses={
        **runs_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),
        422: PROBLEM_RESPONSE_422,
    },
)
def post_run_evolution_promote(
    run_id: UUID,
    body: EvolutionPromoteBody,
    store: StoreDep,
) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    ws = resolve_run_workspace(rows)
    promote_or_reject_prompt(
        store,
        run_id,
        ws,
        artifact_id=body.artifact_id.strip(),
        promote=body.promote,
    )
    rows = store.list_run_events(str(run_id))
    timeline = evolution_timeline_from_rows(rows)
    return {
        "run_id": str(run_id),
        "timeline": timeline,
        "pending": pending_proposals(rows),
        "count": len(timeline),
    }
