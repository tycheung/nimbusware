from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.deps import ProjectStoreDep
from api.errors import problem
from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import enterprise_peel_json_openapi_responses
from iam.context import get_auth_context
from orchestrator.fleet.learnings import search_fleet_learnings, workspaces_for_tenant

router = APIRouter(prefix="/enterprise/fleet-learnings", tags=["enterprise"])


class FleetLearningsSearchResponse(BaseModel):
    """GET /enterprise/fleet-learnings/search (`sak485-f`)."""

    model_config = {"extra": "allow"}

    tenant_id: str | None = None
    query: str | None = None
    workspace_count: int | None = None
    hit_count: int | None = None
    hits: list[dict[str, Any]] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/search",
    response_model=FleetLearningsSearchResponse,
    response_model_exclude_none=True,
    summary="Fleet learnings search (`sak485-f`)",
    responses=enterprise_peel_json_openapi_responses(),  # sak496-e
)
def fleet_learnings_search(
    _gate: EnterpriseDep,
    project_store: ProjectStoreDep,
    q: Annotated[str, Query(min_length=1, max_length=512)],
    k: Annotated[int, Query(ge=1, le=50)] = 10,
) -> dict[str, Any]:
    ctx = get_auth_context()
    if ctx is None:
        raise HTTPException(
            status_code=401,
            detail=problem("unauthorized", "missing authenticated IAM context"),
        )
    workspaces = workspaces_for_tenant(project_store, ctx.tenant_id)
    hits = search_fleet_learnings(workspaces, q, limit=k)
    return {
        "tenant_id": str(ctx.tenant_id),
        "query": q,
        "workspace_count": len(workspaces),
        "hit_count": len(hits),
        "hits": hits,
    }
