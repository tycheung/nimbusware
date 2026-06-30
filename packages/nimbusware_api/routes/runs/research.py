from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent_core.models import (
    EventType,
    ResearchBriefApprovedEvent,
    ResearchBriefRejectedEvent,
    ResearchBriefReviewPayload,
)
from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_projections.builders.run_research import run_research_briefs_from_events
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422

router = APIRouter()


class ResearchBriefsResponse(BaseModel):
    run_id: str
    briefs: list[dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class ResearchReviewBody(BaseModel):
    notes: str = Field(default="", max_length=2000)


@router.get(
    "/runs/{run_id}/research",
    response_model=ResearchBriefsResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_run_research(run_id: UUID, store: StoreDep) -> ResearchBriefsResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    body = run_research_briefs_from_events(rows)
    return ResearchBriefsResponse(run_id=str(run_id), **body)


def _find_brief(rows: list[dict[str, Any]], brief_id: str) -> dict[str, Any] | None:
    body = run_research_briefs_from_events(rows)
    for b in body.get("briefs") or []:
        if isinstance(b, dict) and str(b.get("brief_id")) == brief_id:
            return b
    return None


@router.post(
    "/runs/{run_id}/research/{brief_id}/approve",
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def post_research_approve(
    run_id: UUID,
    brief_id: str,
    body: ResearchReviewBody,
    store: StoreDep,
) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    brief = _find_brief(rows, brief_id)
    if brief is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "brief_not_found", "research brief not found", details={"brief_id": brief_id}
            ),
        )
    if brief.get("status") != "pending":
        raise HTTPException(
            status_code=422,
            detail=problem("brief_not_pending", f"brief status is {brief.get('status')}"),
        )
    kind = brief.get("brief_kind")
    if kind not in ("domain", "code"):
        kind = "domain"
    brief_kind = cast(Literal["domain", "code"], kind)
    store.append(
        ResearchBriefApprovedEvent(
            event_type=EventType.RESEARCH_BRIEF_APPROVED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ResearchBriefReviewPayload(
                artifact_id=brief_id,
                brief_kind=brief_kind,
                notes=body.notes,
            ),
        ),
    )
    return {"status": "approved", "brief_id": brief_id}


@router.post(
    "/runs/{run_id}/research/{brief_id}/reject",
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def post_research_reject(
    run_id: UUID,
    brief_id: str,
    body: ResearchReviewBody,
    store: StoreDep,
) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    brief = _find_brief(rows, brief_id)
    if brief is None:
        raise HTTPException(
            status_code=404,
            detail=problem(
                "brief_not_found", "research brief not found", details={"brief_id": brief_id}
            ),
        )
    if brief.get("status") != "pending":
        raise HTTPException(
            status_code=422,
            detail=problem("brief_not_pending", f"brief status is {brief.get('status')}"),
        )
    kind = brief.get("brief_kind")
    if kind not in ("domain", "code"):
        kind = "domain"
    brief_kind = cast(Literal["domain", "code"], kind)
    store.append(
        ResearchBriefRejectedEvent(
            event_type=EventType.RESEARCH_BRIEF_REJECTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=ResearchBriefReviewPayload(
                artifact_id=brief_id,
                brief_kind=brief_kind,
                notes=body.notes,
            ),
        ),
    )
    return {"status": "rejected", "brief_id": brief_id}
