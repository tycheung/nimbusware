"""Read-only scraper artifact inventory."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Query

from nimbusware_api.deps import OrchDep
from nimbusware_api.schemas.openapi import (
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
    SCRAPER_ARTIFACT_INVENTORY_RESPONSE_200,
)
from nimbusware_api.schemas.scraper_artifacts import ScraperArtifactInventoryResponse
from nimbusware_orchestrator.scraper_artifacts import (
    resolve_scraper_artifact_base_dir,
    scraper_artifact_inventory,
)

router = APIRouter(tags=["scraper-artifacts"])

INVENTORY_MAX_ENTRIES = 500


@router.get(
    "/scraper-artifacts/inventory",
    response_model=ScraperArtifactInventoryResponse,
    responses={
        200: SCRAPER_ARTIFACT_INVENTORY_RESPONSE_200,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def get_scraper_artifact_inventory(
    orch: OrchDep,
    max_entries: Annotated[
        int,
        Query(ge=1, le=INVENTORY_MAX_ENTRIES, description="Cap listed file rows"),
    ] = 100,
) -> ScraperArtifactInventoryResponse:
    """On-disk scraper artifact inventory under the configured cache directory."""
    base = resolve_scraper_artifact_base_dir(orch.repo_root)
    env_days = os.environ.get("NIMBUSWARE_SCRAPER_ARTIFACT_MAX_AGE_DAYS", "").strip()
    retention_days: int | None = None
    if env_days:
        try:
            days = int(env_days)
        except ValueError:
            days = 0
        if days >= 1:
            retention_days = days
    raw = scraper_artifact_inventory(
        base,
        max_entries=max_entries,
        retention_max_age_days=retention_days,
    )
    if retention_days is not None:
        raw["retention_max_age_days"] = retention_days
    return ScraperArtifactInventoryResponse.model_validate(raw)
