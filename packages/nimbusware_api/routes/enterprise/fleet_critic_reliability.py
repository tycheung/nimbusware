from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query

from nimbusware_api.deps import StoreDep
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_orchestrator.fleet_critic_reliability import tenant_critic_reliability_metrics

router = APIRouter(prefix="/enterprise/fleet/critic-reliability", tags=["enterprise"])


@router.get("")
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
