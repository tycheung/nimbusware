"""Enterprise object-store primary status."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from nimbusware_api.routes.enterprise.core import EnterpriseDep
from nimbusware_env.edition import enterprise_feature_enabled
from nimbusware_orchestrator.scraper_artifacts_inventory import (
    scraper_artifact_storage_backend_signals,
)

router = APIRouter(prefix="/enterprise/scraper-artifacts", tags=["enterprise"])


@router.get("/storage")
def scraper_artifact_storage_status(_gate: EnterpriseDep) -> dict[str, Any]:
    sig = scraper_artifact_storage_backend_signals()
    return {
        "feature": "object_store_primary",
        "enabled": enterprise_feature_enabled("object_store_primary"),
        "signals": sig,
    }
