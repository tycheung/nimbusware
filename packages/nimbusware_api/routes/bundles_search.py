from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from nimbusware_api.deps import OrchDep
from nimbusware_api.routes.bundles_helpers import hit_from_row
from nimbusware_api.schemas.bundles import BundleSearchHit, BundleSearchResponse
from nimbusware_api.schemas.openapi import (
    BUNDLE_SEARCH_RESPONSE_200,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
)
from nimbusware_extensions.catalog import (
    bundle_faiss_index_ready,
    bundle_faiss_index_sync_state,
    search_bundles,
)

router = APIRouter()


@router.get(
    "/search",
    response_model=BundleSearchResponse,
    responses={
        200: BUNDLE_SEARCH_RESPONSE_200,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
    summary="Search bundle catalog",
)
def get_bundle_search(
    orch: OrchDep,
    q: Annotated[
        str,
        Query(
            min_length=1,
            max_length=512,
            description="Space- or comma-separated terms matched against bundle tags and ids.",
        ),
    ],
    k: Annotated[int, Query(ge=1, le=20, description="Maximum number of hits to return.")] = 5,
) -> BundleSearchResponse:
    rows = search_bundles(
        orch.repo_root,
        q,
        k=k,
        config_materializer=getattr(orch, "config_materializer", None),
        bundle_outcome_store=getattr(orch, "_bundle_outcome_store", None),
    )
    hits: list[BundleSearchHit] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        hit = hit_from_row(row)
        if hit is not None and hit.id:
            hits.append(hit)
    sync = bundle_faiss_index_sync_state(orch.repo_root)
    return BundleSearchResponse(
        query=q.strip(),
        k=k,
        hits=hits,
        faiss_index_ready=bundle_faiss_index_ready(orch.repo_root),
        faiss_index_stale=sync.get("stale"),
    )
