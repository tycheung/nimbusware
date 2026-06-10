from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import (
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)
from nimbusware_maker.workspace import run_created_metadata_from_rows
from nimbusware_orchestrator.policy_snapshot_diff import (
    diff_policy_snapshots,
    policy_snapshot_from_run_created_metadata,
)

router = APIRouter(tags=["policy"])


class PolicyDiffResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_a: str
    run_b: str
    identical: bool
    changed_count: int
    changed: list[dict[str, Any]]


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
    return PolicyDiffResponse(
        run_a=ra,
        run_b=rb,
        identical=bool(diff["identical"]),
        changed_count=int(diff["changed_count"]),
        changed=list(diff["changed"]),
    )
