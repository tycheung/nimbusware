from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import StoreDep
from api.errors import problem
from api.schemas.openapi import PROBLEM_RESPONSE_404
from api.schemas.peel_responses import campaign_json_openapi_responses
from projections.builders.backlog_tree import backlog_tree_from_events

router = APIRouter()

_BACKLOG_PENDING_DETAIL = (
    "Campaign exists but no delivery backlog has been emitted yet; "
    "wait for the campaign driver tick or check workflow profile."
)


class CampaignBacklogResponse(BaseModel):
    """GET /campaigns/{campaign_id}/backlog (`sak484-e`)."""

    model_config = {"extra": "allow"}

    campaign_id: str | None = None
    metadata: dict[str, Any] | None = None
    completion_criteria: dict[str, Any] | None = None
    epics: list[dict[str, Any]] | None = None
    summary: dict[str, Any] | None = None
    has_backlog: bool | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/campaigns/{campaign_id}/backlog",
    response_model=CampaignBacklogResponse,
    response_model_exclude_none=True,
    summary="Campaign backlog (`sak484-e`)",
    responses=campaign_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak497-d
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
            detail=problem("backlog_not_found", _BACKLOG_PENDING_DETAIL),
        )
    return tree
