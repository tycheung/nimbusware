from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_api.routes.preflight import get_preflight_history
from nimbusware_env.edition import enterprise_feature_enabled
from nimbusware_orchestrator.fleet_ollama_sli import (
    fleet_ollama_sli_enabled,
    fleet_ollama_sli_status_snapshot,
    merge_preflight_history_aggregate,
)
from nimbusware_orchestrator.fleet_worker import (
    collect_fleet_worker_metrics,
    fleet_redis_worker_enabled,
    fleet_worker_health_snapshot,
)

router = APIRouter(tags=["enterprise"])
ollama_sli_router = APIRouter(prefix="/enterprise/fleet-ollama-sli", tags=["enterprise"])
worker_router = APIRouter(prefix="/enterprise/fleet-worker", tags=["enterprise"])


@ollama_sli_router.get("/status")
def fleet_ollama_sli_status(_gate: EnterpriseDep) -> dict[str, Any]:
    return fleet_ollama_sli_status_snapshot()


@ollama_sli_router.get("/preflight-aggregate")
def fleet_preflight_aggregate(
    _gate: EnterpriseDep,
    store: StoreDep,
    orch: OrchDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    include_metrics_export: Annotated[
        int,
        Query(ge=0, le=1, description="``1`` includes metrics_export on preflight-history"),
    ] = 1,
) -> dict[str, Any]:
    if not fleet_ollama_sli_enabled():
        return {
            "feature": "fleet_ollama_sli",
            "enabled": enterprise_feature_enabled("fleet_ollama_sli"),
            "fleet_profile_enabled": False,
            "message": (
                "Enterprise fleet_ollama_sli is not enabled in this build "
                "(see IMPLEMENTED_ENTERPRISE_FEATURES)."
            ),
        }
    history = get_preflight_history(
        store=store,
        orch=orch,
        limit=limit,
        include_metrics_export=include_metrics_export,
    )
    return merge_preflight_history_aggregate(history.model_dump())


@worker_router.get("/health")
def fleet_worker_health(_gate: EnterpriseDep) -> dict[str, Any]:
    return fleet_worker_health_snapshot()


@worker_router.get("/metrics")
def fleet_worker_metrics(_gate: EnterpriseDep) -> dict[str, Any]:
    if not fleet_redis_worker_enabled():
        return {
            "feature": "redis_fleet_worker",
            "enabled": enterprise_feature_enabled("redis_fleet_worker"),
            "fleet_profile_enabled": False,
            "message": "Set NIMBUSWARE_RUN_DISPATCH=redis and NIMBUSWARE_REDIS_URL with Enterprise edition.",
        }
    return collect_fleet_worker_metrics()
