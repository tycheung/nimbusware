from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query, Request

from api.deps import StoreDep
from env import find_repo_root
from orchestrator.config_blast_radius import preview_workflow_blast_radius

router = APIRouter(tags=["config"])


@router.get("/config/blast-radius")
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
