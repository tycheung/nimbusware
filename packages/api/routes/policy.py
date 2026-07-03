from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from api.deps import StoreDep
from api.errors import problem
from api.schemas.openapi import (
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)
from env.dotenv import find_repo_root
from maker.workspace.workspace import run_created_metadata_from_rows
from orchestrator.policy_snapshot_diff import (
    diff_policy_snapshots,
    policy_snapshot_from_run_created_metadata,
)
from projections.builders.policy_compare_outcome import (
    build_policy_compare_outcome,
    save_policy_compare_outcome,
)

router = APIRouter(tags=["policy"])


class PolicyDiffResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_a: str
    run_b: str
    identical: bool
    changed_count: int
    changed: list[dict[str, Any]]
    gate_outcome: dict[str, Any] | None = None


class PolicyCompareRecordBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_a: UUID
    run_b: UUID


@router.get(
    "/policy/compare",
    response_model=PolicyDiffResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422, 500: PROBLEM_RESPONSE_500},
)
def compare_run_policies(
    store: StoreDep,
    run_a: Annotated[UUID, Query(alias="run_a")],
    run_b: Annotated[UUID, Query(alias="run_b")],
) -> PolicyDiffResponse:
    ra, rb = str(run_a), str(run_b)
    rows_a = store.list_run_events(ra)
    rows_b = store.list_run_events(rb)
    if not rows_a:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run a not found", details={"run_id": ra}),
        )
    if not rows_b:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run b not found", details={"run_id": rb}),
        )
    snap_a = policy_snapshot_from_run_created_metadata(run_created_metadata_from_rows(rows_a))
    snap_b = policy_snapshot_from_run_created_metadata(run_created_metadata_from_rows(rows_b))
    diff = diff_policy_snapshots(snap_a, snap_b)
    outcome = build_policy_compare_outcome(
        store,
        run_a=ra,
        run_b=rb,
        policy_identical=bool(diff["identical"]),
        changed_count=int(diff["changed_count"]),
    )
    save_policy_compare_outcome(find_repo_root(), outcome)
    return PolicyDiffResponse(
        run_a=ra,
        run_b=rb,
        identical=bool(diff["identical"]),
        changed_count=int(diff["changed_count"]),
        changed=list(diff["changed"]),
        gate_outcome=outcome,
    )


@router.post(
    "/policy/compare/record",
    response_model=PolicyDiffResponse,
    responses={404: PROBLEM_RESPONSE_404, 422: PROBLEM_RESPONSE_422, 500: PROBLEM_RESPONSE_500},
)
def record_policy_compare(
    store: StoreDep,
    body: PolicyCompareRecordBody,
) -> PolicyDiffResponse:
    return compare_run_policies(store, run_a=body.run_a, run_b=body.run_b)
