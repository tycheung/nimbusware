from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from api.deps import StoreDep
from api.errors import problem
from orchestrator.campaign.artifact_bundle import build_campaign_artifact_bundle

router = APIRouter()


@router.get("/runs/{run_id}/campaign-artifact-bundle")
def get_campaign_artifact_bundle(run_id: UUID, store: StoreDep) -> dict:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    return build_campaign_artifact_bundle(rows, run_id=run_id)
