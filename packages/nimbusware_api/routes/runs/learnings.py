from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_maker.workspace import resolve_run_workspace
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.learnings_catalog import list_workspace_learnings
from nimbusware_orchestrator.learnings_stitch_suggest import stitch_suggestion_for_run

router = APIRouter()


@router.get(
    "/runs/{run_id}/learnings",
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
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
