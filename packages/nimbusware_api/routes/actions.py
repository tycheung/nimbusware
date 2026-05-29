from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent_core.models import (
    EventType,
    RunEscalatedEvent,
    RunEscalatedPayload,
    StageStartedEvent,
    StageStartedPayload,
)
from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import (
    PROBLEM_RESPONSE_401,
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
    PROBLEM_RESPONSE_503,
)

router = APIRouter(tags=["actions"])


class EscalateBody(BaseModel):
    actor_id: str = Field(min_length=1)
    reason_code: str = Field(min_length=1)
    notes: str | None = None


@router.post(
    "/runs/{run_id}/actions/retry",
    responses={
        200: {
            "description": "Retry stage marker appended",
            "content": {
                "application/json": {"example": {"status": "retry_recorded"}},
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def retry_stage(run_id: UUID, store: StoreDep) -> dict[str, str]:
    rid_s = str(run_id)
    rows = store.list_run_events(rid_s)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": rid_s}),
        )
    rid = run_id
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name="retry", attempt=1),
        ),
    )
    return {"status": "retry_recorded"}


@router.post(
    "/runs/{run_id}/actions/escalate",
    responses={
        200: {
            "description": "Escalation event appended",
            "content": {
                "application/json": {"example": {"status": "escalated"}},
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def escalate(run_id: UUID, body: EscalateBody, store: StoreDep) -> dict[str, str]:
    rid_s = str(run_id)
    rows = store.list_run_events(rid_s)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": rid_s}),
        )
    rid = run_id
    store.append(
        RunEscalatedEvent(
            event_type=EventType.RUN_ESCALATED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=datetime.now(timezone.utc),
            payload=RunEscalatedPayload(
                actor_id=body.actor_id,
                reason_code=body.reason_code,
                notes=body.notes,
            ),
        ),
    )
    return {"status": "escalated"}


@router.post(
    "/roles/{role_id}/execute",
    responses={
        200: {
            "description": "Stub response (executor not wired)",
            "content": {
                "application/json": {
                    "example": {
                        "role_id": "backend_writer",
                        "status": "not_implemented",
                        "detail": "Authenticated stub; wire executor when ready (plan §6.6).",
                    },
                },
            },
        },
        401: PROBLEM_RESPONSE_401,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
        503: PROBLEM_RESPONSE_503,
    },
)
def execute_role(role_id: str, _: AdminDep) -> dict[str, Any]:
    return {
        "role_id": role_id,
        "status": "not_implemented",
        "detail": "Authenticated stub; wire executor when ready (plan §6.6).",
    }
