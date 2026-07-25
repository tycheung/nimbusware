from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from api.routes.enterprise.core import EnterpriseDep
from api.schemas.peel_responses import enterprise_peel_json_openapi_responses
from env.edition import enterprise_feature_enabled
from orchestrator.scraper.artifacts_inventory import (
    scraper_artifact_storage_backend_signals,
)

router = APIRouter(prefix="/enterprise/scraper-artifacts", tags=["enterprise"])


class ScraperArtifactStorageResponse(BaseModel):
    """GET /enterprise/scraper-artifacts/storage (`sak486-e`)."""

    model_config = {"extra": "allow"}

    feature: str | None = None
    enabled: bool | None = None
    signals: dict[str, Any] | None = None
    via: str | None = None
    error: str | None = None


@router.get(
    "/storage",
    response_model=ScraperArtifactStorageResponse,
    response_model_exclude_none=True,
    summary="Scraper artifact storage status (`sak486-e`)",
    responses=enterprise_peel_json_openapi_responses(),  # sak496-e
)
def scraper_artifact_storage_status(_gate: EnterpriseDep) -> dict[str, Any]:
    sig = scraper_artifact_storage_backend_signals()
    return {
        "feature": "object_store_primary",
        "enabled": enterprise_feature_enabled("object_store_primary"),
        "signals": sig,
    }
