from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from nimbusware_api.deps import ProjectStoreDep
from nimbusware_api.errors import problem
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_iam.context import get_auth_context
from nimbusware_orchestrator.fleet_learnings import search_fleet_learnings, workspaces_for_tenant

router = APIRouter(prefix="/enterprise/fleet-learnings", tags=["enterprise"])


@router.get("/search")
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
