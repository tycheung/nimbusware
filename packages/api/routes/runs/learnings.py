from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import StoreDep
from api.errors import problem
from api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from api.schemas.peel_responses import runs_json_openapi_responses
from env import find_repo_root
from maker.workspace.workspace import resolve_run_workspace
from orchestrator.learnings_catalog import list_workspace_learnings
from orchestrator.learnings_stitch_suggest import stitch_suggestion_for_run

router = APIRouter()


class RunLearningsResponse(BaseModel):
    """GET /runs/{run_id}/learnings (`sak485-e`)."""

    model_config = {"extra": "allow"}

    run_id: str | None = None
    learnings: list[dict[str, Any]] | None = None
    count: int | None = None
    stitch_suggestion: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/runs/{run_id}/learnings",
    response_model=RunLearningsResponse,
    response_model_exclude_none=True,
    summary="Run learnings (`sak485-e`)",
    responses={
        **runs_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak496-f
        422: PROBLEM_RESPONSE_422,
    },
)
def get_run_learnings(run_id: UUID, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    ws = resolve_run_workspace(rows)
    if not ws.is_dir():
        raise HTTPException(
            status_code=422,
            detail=problem("workspace_not_found", "run has no attached workspace"),
        )
    items = list_workspace_learnings(ws)
    suggestion = stitch_suggestion_for_run(rows, find_repo_root())
    body: dict[str, Any] = {"run_id": str(run_id), "learnings": items, "count": len(items)}
    if suggestion:
        body["stitch_suggestion"] = suggestion
    return body
