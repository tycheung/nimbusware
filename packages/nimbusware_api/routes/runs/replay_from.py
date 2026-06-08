from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404, PROBLEM_RESPONSE_422
from nimbusware_orchestrator.replay_from import ReplayPolicy, emit_replay_started_event

router = APIRouter()


class ReplayFromBody(BaseModel):
    from_store_seq: int = Field(ge=0)
    operator_ack: bool = False
    compact_enabled: bool = True
    ignore_compaction_ids: list[str] = Field(default_factory=list)
    ignore_revert_ids: list[str] = Field(default_factory=list)
    reason: str = Field(default="", max_length=500)


class ReplayFromResponse(BaseModel):
    run_id: str
    from_store_seq: int
    replay_started: bool
    compact_enabled: bool


@router.post(
    "/runs/{run_id}/replay-from",
    response_model=ReplayFromResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422},
)
def replay_from_checkpoint(
    run_id: UUID,
    body: ReplayFromBody,
    store: StoreDep,
) -> ReplayFromResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    if not body.operator_ack:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "operator_ack_required",
                "replay-from requires operator_ack=true",
            ),
        )
    policy = ReplayPolicy(
        compact_enabled=body.compact_enabled,
        ignore_compaction_ids=tuple(
            str(x).strip() for x in body.ignore_compaction_ids if str(x).strip()
        ),
        ignore_revert_ids=tuple(str(x).strip() for x in body.ignore_revert_ids if str(x).strip()),
    )
    emit_replay_started_event(
        store,
        run_id=run_id,
        from_store_seq=body.from_store_seq,
        replay_policy=policy,
        operator_ack=True,
        reason=body.reason,
    )
    return ReplayFromResponse(
        run_id=str(run_id),
        from_store_seq=body.from_store_seq,
        replay_started=True,
        compact_enabled=policy.compact_enabled,
    )
