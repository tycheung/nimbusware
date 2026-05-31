"""Enterprise fleet Ollama SLI + preflight aggregate."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from hermes_orchestrator.fleet_ollama_sli import (
    fleet_ollama_sli_enabled,
    fleet_ollama_sli_status_snapshot,
    merge_preflight_history_aggregate,
)
from nimbusware_api.deps import StoreDep
from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_api.routes.preflight import get_preflight_history
from nimbusware_env.edition import enterprise_feature_enabled

router = APIRouter(prefix="/enterprise/fleet-ollama-sli", tags=["enterprise"])


@router.get("/status")
def fleet_ollama_sli_status(_gate: EnterpriseDep) -> dict[str, Any]:
    return fleet_ollama_sli_status_snapshot()


@router.get("/preflight-aggregate")
def fleet_preflight_aggregate(
    _gate: EnterpriseDep,
    store: StoreDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
    include_metrics_export: Annotated[
        int,
        Query(ge=0, le=1, description="``1`` includes metrics_export on preflight-history"),
    ] = 1,
) -> dict[str, Any]:
    """``GET /v1/preflight-history`` aggregates plus on-disk sustained p95 export."""
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
        limit=limit,
        include_metrics_export=include_metrics_export,
    )
    return merge_preflight_history_aggregate(history.model_dump())
