from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_orchestrator.context_compaction import (
    emit_compaction_revert_event,
    find_compaction_event,
    reverted_compaction_ids,
)

router = APIRouter()


class CompactionRevertBody(BaseModel):
    reason: str = Field(default="", max_length=2000)
    reverted_by: str = Field(default="operator", min_length=1, max_length=200)


class CompactionRevertResponse(BaseModel):
    run_id: str
    compaction_id: str
    reverted: bool
    reverted_by: str
    reason: str


@router.post(
    "/runs/{run_id}/compactions/{compaction_id}/revert",
    response_model=CompactionRevertResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def revert_compaction(
    run_id: UUID,
    compaction_id: str,
    body: CompactionRevertBody,
    store: StoreDep,
) -> CompactionRevertResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    target = compaction_id.strip()
    if not target:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", "compaction_id required"),
        )
    if find_compaction_event(rows, target) is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "compaction_not_found",
                "compaction not found",
                details={"compaction_id": target},
            ),
        )
    if target in reverted_compaction_ids(rows):
        return CompactionRevertResponse(
            run_id=str(run_id),
            compaction_id=target,
            reverted=True,
            reverted_by=body.reverted_by.strip(),
            reason=body.reason.strip(),
        )
    emit_compaction_revert_event(
        store,
        run_id=run_id,
        compaction_id=target,
        reverted_by=body.reverted_by,
        reason=body.reason,
    )
    return CompactionRevertResponse(
        run_id=str(run_id),
        compaction_id=target,
        reverted=True,
        reverted_by=body.reverted_by.strip(),
        reason=body.reason.strip(),
    )
