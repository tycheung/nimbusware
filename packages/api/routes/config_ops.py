from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from api.deps import StoreDep
from api.schemas.peel_responses import with_long_tail_peel_503
from env import find_repo_root
from orchestrator.config_blast_radius import preview_workflow_blast_radius

router = APIRouter(tags=["config"])


class ConfigBlastRadiusResponse(BaseModel):
    """GET /config/blast-radius (`sak487-f`)."""

    model_config = {"extra": "allow"}

    workflow_profile: str | None = None
    proposed_effective: dict[str, Any] | None = None
    affected_run_count: int | None = None
    affected_runs: list[dict[str, Any]] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/config/blast-radius",
    response_model=ConfigBlastRadiusResponse,
    response_model_exclude_none=True,
    responses=with_long_tail_peel_503(),  # sak505-c
)
def config_blast_radius(
    request: Request,
    store: StoreDep,
    workflow_profile: Annotated[str, Query(min_length=1)],
    run_limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, Any]:
    mat = getattr(request.app.state, "config_materializer", None)
    return preview_workflow_blast_radius(
        repo_root=find_repo_root(),
        store=store,
        workflow_profile=workflow_profile.strip(),
        run_limit=run_limit,
        config_materializer=mat,
    )
