from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import StoreDep
from api.errors import problem
from api.schemas.openapi import PROBLEM_RESPONSE_404
from projections.builders.context_budget import estimate_context_budget

router = APIRouter()


class ContextBudgetComponents(BaseModel):
    slice_packet_chars: int = 0
    handoff_chars: int = 0
    compaction_summary_chars: int = 0


class ContextBudgetResponse(BaseModel):
    run_id: str
    estimated_chars: int = 0
    estimated_tokens: int = 0
    window_tokens: int = 0
    utilization_ratio: float = 0.0
    advisory_level: str = "green"
    components: ContextBudgetComponents = Field(default_factory=ContextBudgetComponents)
    advisory_only: bool = True


@router.get(
    "/runs/{run_id}/context_budget",
    response_model=ContextBudgetResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_context_budget(run_id: UUID, store: StoreDep) -> ContextBudgetResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    body = estimate_context_budget(rows)
    body["run_id"] = str(run_id)
    return ContextBudgetResponse.model_validate(body)
