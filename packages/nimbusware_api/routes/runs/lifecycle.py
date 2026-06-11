from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Query
from fastapi.routing import APIRouter

from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import (
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)

router = APIRouter()


@router.post(
    "/runs/{run_id}/lifecycle/start",
    responses={
        200: {
            "description": "Preflight completed and run started",
            "content": {
                "application/json": {"example": {"status": "started"}},
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def lifecycle_start(run_id: UUID, orch: OrchDep, store: StoreDep) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    orch.start_run_after_preflight(run_id)
    return {"status": "started"}


@router.post(
    "/runs/{run_id}/lifecycle/plan",
    responses={
        200: {
            "description": "Plan stage recorded",
            "content": {
                "application/json": {"example": {"status": "plan_stage_recorded"}},
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def lifecycle_plan(run_id: UUID, orch: OrchDep, store: StoreDep) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    orch.execute_plan_stage(run_id)
    return {"status": "plan_stage_recorded"}


@router.post(
    "/runs/{run_id}/lifecycle/verify",
    responses={
        200: {
            "description": "Writer/verifier pass recorded",
            "content": {
                "application/json": {
                    "example": {"status": "verify_recorded", "dispatch": "sync"},
                },
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def lifecycle_verify(run_id: UUID, orch: OrchDep, store: StoreDep) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    repo = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()

    host: Any = orch
    dispatch = host.dispatch_or_run_verify(run_id, workspace=repo)
    return {"status": "verify_recorded", "dispatch": dispatch}


@router.post(
    "/runs/{run_id}/lifecycle/slice",
    responses={
        200: {
            "description": "Micro-slice pass recorded",
            "content": {
                "application/json": {
                    "example": {
                        "status": "micro_slice_recorded",
                        "slices_completed": 2,
                        "slices_blocked": 0,
                    },
                },
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def lifecycle_slice(
    run_id: UUID,
    orch: OrchDep,
    store: StoreDep,
    mode: str = Query(
        default="default",
        description="default: maker-aware; auto: full micro-slice pass without approval gates",
    ),
) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    from nimbusware_maker.approval import maker_approval_enabled_from_rows
    from nimbusware_maker.slice_workflow import prepare_next_pending_slice

    if maker_approval_enabled_from_rows(rows) and mode != "auto":
        return prepare_next_pending_slice(orch, run_id)

    repo = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    from nimbusware_maker.workspace import resolve_run_workspace

    ws = resolve_run_workspace(rows, override=repo)
    results = orch.execute_micro_slice_pass(run_id, workspace=ws)
    completed = sum(1 for g in results if g.passed)
    blocked = len(results) - completed
    return {
        "status": "micro_slice_recorded",
        "slices_completed": completed,
        "slices_blocked": blocked,
    }
