from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query

from nimbusware_orchestrator.fleet_analytics import compare_tenant_metrics, tenant_run_metrics
from nimbusware_api.deps import StoreDep
from nimbusware_api.routes.enterprise.core import EnterpriseDep

router = APIRouter(prefix="/enterprise/fleet/analytics", tags=["enterprise"])


@router.get("/compare")
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


@router.get("/tenant/{tenant_id}")
def fleet_analytics_tenant(
    _gate: EnterpriseDep,
    store: StoreDep,
    tenant_id: UUID,
    run_limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    return tenant_run_metrics(store, tenant_id=tenant_id, run_limit=run_limit)
