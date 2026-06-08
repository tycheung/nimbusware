from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_orchestrator.interjection_queue import InterjectionPriority, queue_for_run

router = APIRouter()


class InterjectionEnqueueBody(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    priority: str = "next"
    force_break: bool = False


class InterjectionQueueResponse(BaseModel):
    run_id: str
    queue: dict = Field(default_factory=dict)


@router.get(
    "/runs/{run_id}/interjection-queue",
    response_model=InterjectionQueueResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_interjection_queue(run_id: UUID, store: StoreDep) -> InterjectionQueueResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    q = queue_for_run(str(run_id))
    return InterjectionQueueResponse(run_id=str(run_id), queue=q.to_dict())


@router.post(
    "/runs/{run_id}/interjection-queue",
    response_model=InterjectionQueueResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def post_interjection_enqueue(
    run_id: UUID,
    body: InterjectionEnqueueBody,
    store: StoreDep,
) -> InterjectionQueueResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    priority = (
        InterjectionPriority.LAST
        if body.priority.strip().lower() == "last"
        else InterjectionPriority.NEXT
    )
    q = queue_for_run(str(run_id))
    q.enqueue(
        body.message,
        priority=priority,
        force_break=body.force_break,
    )
    return InterjectionQueueResponse(run_id=str(run_id), queue=q.to_dict())
