from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent_core.models import EventType
from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_research.stitch_outcome_stats import transplant_outcome_for_run

router = APIRouter()

_STITCH_EVENT_TYPES = frozenset(
    {
        EventType.STITCH_PLAN_EMITTED.value,
        EventType.STITCH_APPLIED.value,
        EventType.STITCH_FAILED.value,
        EventType.STITCH_LICENSE_CHECKED.value,
        EventType.STITCH_DEPENDENCY_CHECKED.value,
    },
)


class StitchSummaryResponse(BaseModel):
    run_id: str
    events: list[dict[str, Any]] = Field(default_factory=list)
    transplant_outcome: str | None = None


@router.get(
    "/runs/{run_id}/stitch-summary",
    response_model=StitchSummaryResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_run_stitch_summary(run_id: UUID, store: StoreDep) -> StitchSummaryResponse:
    rid = str(run_id)
    rows = store.list_run_events(rid)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": rid}),
        )
    rows.sort(key=lambda r: int(r.get("store_seq") or 0))
    events: list[dict[str, Any]] = []
    for row in rows:
        et = str(row.get("event_type") or "")
        if et not in _STITCH_EVENT_TYPES:
            continue
        seq = int(row.get("store_seq") or 0)
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        summary_line = ""
        if et == EventType.STITCH_PLAN_EMITTED.value:
            summary_line = str(
                payload.get("candidate_id") or payload.get("manifest_id") or "plan emitted"
            )
        elif et == EventType.STITCH_APPLIED.value:
            summary_line = f"applied {len(payload.get('file_paths') or [])} paths"
        elif et == EventType.STITCH_FAILED.value:
            summary_line = str(payload.get("reason_code") or "stitch failed")
        else:
            summary_line = et.split(".", 1)[-1]
        events.append(
            {
                "store_seq": seq,
                "event_type": et,
                "summary": summary_line[:500],
                "payload": payload,
            },
        )
    outcome = transplant_outcome_for_run(rows)
    return StitchSummaryResponse(run_id=rid, events=events, transplant_outcome=outcome)
