from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.read_models.maker_progress import (
    maker_progress_from_events,
    strip_operator_fields,
)
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404

router = APIRouter()


class MakerProgressResponse(BaseModel):
    run_id: str
    status: str
    run_status: str
    plan_summary: str
    slice_index: int
    slice_total: int
    slices_completed: int
    current_headline: str
    sentences: list[str] = Field(default_factory=list)
    slices: list[dict[str, Any]] = Field(default_factory=list)
    requirements: dict[str, Any] | None = None
    resource_pressure: dict[str, Any] | None = None
    context_budget: dict[str, Any] | None = None
    campaign_progress: dict[str, Any] | None = None
    latest_handoff: dict[str, Any] | None = None
    simple_mode: bool = True


@router.get(
    "/runs/{run_id}/maker-progress",
    response_model=MakerProgressResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_maker_progress(
    run_id: UUID,
    store: StoreDep,
    simple: bool = Query(default=True, description="Strip operator telemetry fields"),
) -> MakerProgressResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    body = maker_progress_from_events(rows)
    if simple:
        body = strip_operator_fields(body)
    body["run_id"] = str(run_id)
    return MakerProgressResponse.model_validate(body)
