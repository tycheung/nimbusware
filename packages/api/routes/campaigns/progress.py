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
from projections.builders.campaign_progress import campaign_progress_from_events

router = APIRouter()


class CampaignProgressResponse(BaseModel):
    """GET /campaigns/{campaign_id}/progress (`sak484-e`)."""

    model_config = {"extra": "allow"}

    progress: dict[str, Any] | None = None
    backlog: dict[str, Any] | None = None
    maintenance_events: list[Any] | None = None
    completion_evaluations: list[Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/campaigns/{campaign_id}/progress",
    response_model=CampaignProgressResponse,
    response_model_exclude_none=True,
    summary="Campaign progress (`sak484-e`)",
    responses=campaign_json_openapi_responses(not_found=PROBLEM_RESPONSE_404),  # sak497-d
)
def get_campaign_progress(campaign_id: UUID, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(campaign_id))
    if not rows:
        raise HTTPException(status_code=404, detail=problem("run_not_found", "campaign not found"))
    progress = campaign_progress_from_events(rows)
    if progress is None:
        raise HTTPException(
            status_code=404, detail=problem("campaign_not_found", "not a campaign run")
        )
    maintenance = [
        r.get("event_type")
        for r in rows
        if str(r.get("event_type") or "").startswith("maintenance.")
    ]
    completion = [r.get("payload") for r in rows if r.get("event_type") == "completion.evaluated"]
    return {
        "progress": progress,
        "backlog": backlog_tree_from_events(rows),
        "maintenance_events": maintenance[-20:],
        "completion_evaluations": completion[-10:],
    }
