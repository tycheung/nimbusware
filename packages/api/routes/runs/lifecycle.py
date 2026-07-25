from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, Query
from fastapi.routing import APIRouter
from pydantic import BaseModel

from api.deps import OrchDep, StoreDep
from api.errors import problem
from api.schemas.openapi import (
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)
from api.schemas.peel_responses import with_long_tail_peel_503
from env.env_flags import nimbusware_repo_root_path

router = APIRouter()


class LifecycleStartResponse(BaseModel):
    """POST /runs/{run_id}/lifecycle/start (`sak486-g`)."""

    model_config = {"extra": "allow"}

    status: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class LifecyclePlanResponse(BaseModel):
    """POST /runs/{run_id}/lifecycle/plan (`sak486-g`)."""

    model_config = {"extra": "allow"}

    status: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class LifecycleVerifyResponse(BaseModel):
    """POST /runs/{run_id}/lifecycle/verify (`sak486-g`)."""

    model_config = {"extra": "allow"}

    status: str | None = None
    dispatch: str | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class LifecycleSliceResponse(BaseModel):
    """POST /runs/{run_id}/lifecycle/slice (`sak486-g`)."""

    model_config = {"extra": "allow"}

    status: str | None = None
    dispatch: str | None = None
    slices_completed: int | None = None
    slices_blocked: int | None = None
    slice_total: int | None = None
    pending: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.post(
    "/runs/{run_id}/lifecycle/start",
    response_model=LifecycleStartResponse,
    response_model_exclude_none=True,
    responses=with_long_tail_peel_503(  # sak502-g
        {
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
    ),
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
    response_model=LifecyclePlanResponse,
    response_model_exclude_none=True,
    responses=with_long_tail_peel_503(  # sak504-h
        {
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
    ),
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
    response_model=LifecycleVerifyResponse,
    response_model_exclude_none=True,
    responses=with_long_tail_peel_503(  # sak504-h
        {
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
    ),
)
def lifecycle_verify(run_id: UUID, orch: OrchDep, store: StoreDep) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    repo = nimbusware_repo_root_path()

    host: Any = orch
    dispatch = host.dispatch_or_run_verify(run_id, workspace=repo)
    return {"status": "verify_recorded", "dispatch": dispatch}


@router.post(
    "/runs/{run_id}/lifecycle/slice",
    response_model=LifecycleSliceResponse,
    response_model_exclude_none=True,
    responses=with_long_tail_peel_503(  # sak504-h
        {
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
    ),
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
    from maker.approval import maker_approval_enabled_from_rows
    from maker.slice_workflow import prepare_next_pending_slice

    if maker_approval_enabled_from_rows(rows) and mode != "auto":
        return prepare_next_pending_slice(orch, run_id)

    repo = nimbusware_repo_root_path()
    from maker.workspace.workspace import resolve_run_workspace

    ws = resolve_run_workspace(rows, override=repo)
    results = orch.execute_micro_slice_pass(run_id, workspace=ws)
    completed = sum(1 for g in results if g.passed)
    blocked = len(results) - completed
    return {
        "status": "micro_slice_recorded",
        "slices_completed": completed,
        "slices_blocked": blocked,
    }
