from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.deps import StoreDep
from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import enterprise_peel_json_openapi_responses
from orchestrator.fleet.critic_reliability import tenant_critic_reliability_metrics

router = APIRouter(prefix="/enterprise/fleet/critic-reliability", tags=["enterprise"])


class FleetCriticReliabilityResponse(BaseModel):
    """GET /enterprise/fleet/critic-reliability (`sak485-f`)."""

    model_config = {"extra": "allow"}

    tenant_id: str | None = None
    runs_scanned: int | None = None
    runs_with_critics: int | None = None
    critic_verdict_count: int | None = None
    critic_fail_count: int | None = None
    critic_fail_rate: float | None = None
    in_domain_verdict_count: int | None = None
    in_domain_fail_count: int | None = None
    in_domain_fail_rate: float | None = None
    out_of_domain_verdict_count: int | None = None
    out_of_domain_fail_count: int | None = None
    out_of_domain_rate: float | None = None
    gate_block_count: int | None = None
    repeat_finding_paths: int | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "",
    response_model=FleetCriticReliabilityResponse,
    response_model_exclude_none=True,
    summary="Fleet critic reliability (`sak485-f`)",
    responses=enterprise_peel_json_openapi_responses(),  # sak496-e
)
def fleet_critic_reliability(
    _gate: EnterpriseDep,
    store: StoreDep,
    tenant_id: Annotated[UUID, Query()],
    run_limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    return tenant_critic_reliability_metrics(
        store,
        tenant_id=tenant_id,
        run_limit=run_limit,
    )
