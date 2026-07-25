from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.deps import StoreDep
from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import enterprise_peel_json_openapi_responses
from orchestrator.fleet.analytics import compare_tenant_metrics, tenant_run_metrics

router = APIRouter(prefix="/enterprise/fleet/analytics", tags=["enterprise"])


class FleetAnalyticsCompareResponse(BaseModel):
    """GET /enterprise/fleet/analytics/compare (`sak485-f`)."""

    model_config = {"extra": "allow"}

    tenant_a: dict[str, Any] | None = None
    tenant_b: dict[str, Any] | None = None
    comparison: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


class FleetAnalyticsTenantResponse(BaseModel):
    """GET /enterprise/fleet/analytics/tenant/{tenant_id} (`sak485-f`)."""

    model_config = {"extra": "allow"}

    tenant_id: str | None = None
    runs_scanned: int | None = None
    gate_metrics: dict[str, Any] | None = None
    ollama_sli: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None
    feature: str | None = None


@router.get(
    "/compare",
    response_model=FleetAnalyticsCompareResponse,
    response_model_exclude_none=True,
    summary="Fleet analytics compare (`sak485-f`)",
    responses=enterprise_peel_json_openapi_responses(),  # sak495-c
)
def fleet_analytics_compare(
    _gate: EnterpriseDep,
    store: StoreDep,
    tenant_a: Annotated[UUID, Query()],
    tenant_b: Annotated[UUID, Query()],
    run_limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    return compare_tenant_metrics(
        store,
        tenant_a=tenant_a,
        tenant_b=tenant_b,
        run_limit=run_limit,
    )


@router.get(
    "/tenant/{tenant_id}",
    response_model=FleetAnalyticsTenantResponse,
    response_model_exclude_none=True,
    summary="Fleet analytics tenant (`sak485-f`)",
    responses=enterprise_peel_json_openapi_responses(),  # sak495-c
)
def fleet_analytics_tenant(
    _gate: EnterpriseDep,
    store: StoreDep,
    tenant_id: UUID,
    run_limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    return tenant_run_metrics(store, tenant_id=tenant_id, run_limit=run_limit)
