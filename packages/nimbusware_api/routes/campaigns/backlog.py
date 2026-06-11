from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_projections.builders.backlog_tree import backlog_tree_from_events

router = APIRouter()


@router.get(
    "/campaigns/{campaign_id}/backlog",
    responses={404: PROBLEM_RESPONSE_404},
)
def get_campaign_backlog(campaign_id: UUID, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(campaign_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "run_not_found", "campaign not found", details={"campaign_id": str(campaign_id)}
            ),
        )
    tree = backlog_tree_from_events(rows)
    if tree is None:
        raise HTTPException(
            status_code=404,
            detail=problem("backlog_not_found", "delivery backlog not yet generated"),
        )
    return tree
