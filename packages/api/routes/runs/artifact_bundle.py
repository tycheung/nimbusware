from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.deps import StoreDep
from api.errors import problem
from api.schemas.peel_responses import with_long_tail_peel_503
from orchestrator.campaign.artifact_bundle import build_campaign_artifact_bundle

router = APIRouter()


class CampaignArtifactBundleResponse(BaseModel):
    """GET /runs/{run_id}/campaign-artifact-bundle (`sak484-f`)."""

    model_config = {"extra": "allow"}

    version: int | None = None
    run_id: str | None = None
    allowed_sources: list[str] | None = None
    forbidden_omitted: list[str] | None = None
    sources: dict[str, Any] | None = None
    checksum_sha256: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/runs/{run_id}/campaign-artifact-bundle",
    response_model=CampaignArtifactBundleResponse,
    response_model_exclude_none=True,
    summary="Campaign artifact bundle export (`sak484-f`)",
    responses=with_long_tail_peel_503(),  # sak507-i
)
def get_campaign_artifact_bundle(run_id: UUID, store: StoreDep) -> dict:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    return build_campaign_artifact_bundle(rows, run_id=run_id)
