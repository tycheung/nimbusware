from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.deps import StoreDep
from api.errors import problem
from api.schemas.openapi import PROBLEM_RESPONSE_404
from iam.context import get_auth_context
from orchestrator.profiles.enforcement_profiles import (
    EnforcementProfile,
    enforcement_profile_from_rows,
    persist_run_enforcement,
    resolve_enforcement_profile,
)

router = APIRouter()


class RunEnforcementBody(BaseModel):
    level: int = Field(ge=0, le=10, default=5)


class RunEnforcementResponse(BaseModel):
    run_id: str
    level: int
    name: str
    ruff_scope: str
    ruff_format_check: bool
    tests_mode: str
    coverage_floor: float | None = None
    security_mode: str
    pip_audit: str
    e2e_mode: str
    universal_critique: bool
    fast_slice_allowed: bool
    skip_verdict_policy: str
    milestone_full_ci: bool
    terminal_parity_ci: bool
    custom: bool = False


def _response_from_profile(run_id: str, profile: EnforcementProfile) -> RunEnforcementResponse:
    d = profile.to_dict()
    return RunEnforcementResponse(run_id=run_id, **d)


@router.get(
    "/runs/{run_id}/enforcement",
    response_model=RunEnforcementResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def get_run_enforcement(run_id: UUID, store: StoreDep) -> RunEnforcementResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    profile = enforcement_profile_from_rows(rows)
    return _response_from_profile(str(run_id), profile)


@router.put(
    "/runs/{run_id}/enforcement",
    response_model=RunEnforcementResponse,
    responses={404: PROBLEM_RESPONSE_404},
)
def put_run_enforcement(
    run_id: UUID,
    body: RunEnforcementBody,
    store: StoreDep,
) -> RunEnforcementResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    profile = resolve_enforcement_profile(level=body.level)
    ctx = get_auth_context()
    profile = persist_run_enforcement(
        store,
        run_id,
        profile,
        tenant_slug=ctx.tenant_slug if ctx else None,
    )
    return _response_from_profile(str(run_id), profile)
