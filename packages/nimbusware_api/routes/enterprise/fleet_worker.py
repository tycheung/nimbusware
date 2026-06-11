from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_env.edition import enterprise_feature_enabled
from nimbusware_orchestrator.fleet_worker import (
    collect_fleet_worker_metrics,
    fleet_redis_worker_enabled,
    fleet_worker_health_snapshot,
)

router = APIRouter(prefix="/enterprise/fleet-worker", tags=["enterprise"])


@router.get("/health")
def fleet_worker_health(_gate: EnterpriseDep) -> dict[str, Any]:
    return fleet_worker_health_snapshot()


@router.get("/metrics")
def fleet_worker_metrics(_gate: EnterpriseDep) -> dict[str, Any]:
    if not fleet_redis_worker_enabled():
        return {
            "feature": "redis_fleet_worker",
            "enabled": enterprise_feature_enabled("redis_fleet_worker"),
            "fleet_profile_enabled": False,
            "message": "Set NIMBUSWARE_RUN_DISPATCH=redis and NIMBUSWARE_REDIS_URL with Enterprise edition.",
        }
    return collect_fleet_worker_metrics()
