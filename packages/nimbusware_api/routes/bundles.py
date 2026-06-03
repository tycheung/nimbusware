from __future__ import annotations

from copy import deepcopy
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from hermes_extensions.catalog import (
    bundle_faiss_index_ready,
    bundle_faiss_index_sync_state,
    search_bundles,
    validate_bundle_catalog_content,
)
from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import OrchDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.bundles import (
    BundleCatalogEntry,
    BundleCatalogPatchRequest,
    BundleCatalogPutRequest,
    BundleCatalogResponse,
    BundleSearchHit,
    BundleSearchResponse,
)
from nimbusware_api.schemas.openapi import (
    BUNDLE_SEARCH_RESPONSE_200,
    PROBLEM_RESPONSE_401,
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
    PROBLEM_RESPONSE_503,
)
from nimbusware_config.persist import load_bundle_catalog_dict, persist_bundle_catalog_dict

router = APIRouter(prefix="/bundles", tags=["bundles"])


def _config_materializer(orch: Any) -> Any | None:
    return getattr(orch, "config_materializer", None)


def _load_catalog_raw(orch: Any) -> dict[str, Any]:
    mat = _config_materializer(orch)
    try:
        raw = load_bundle_catalog_dict(orch.repo_root, materializer=mat)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail=problem(
                "bundle_catalog_unavailable",
                "bundle catalog is missing under the frozen repo root",
            ),
        ) from None
    except KeyError as exc:
        raise HTTPException(
            status_code=503,
            detail=problem(
                "bundle_catalog_unavailable",
                "bundle catalog document is missing in config store",
                details={"reason": str(exc)},
            ),
        ) from exc
    if not isinstance(raw, dict):
        raise HTTPException(
            status_code=500,
            detail=problem("bundle_catalog_invalid", "bundle catalog must be a mapping"),
        )
    return raw


def _catalog_response(orch: Any, raw: dict[str, Any]) -> BundleCatalogResponse:
    bundles_raw = raw.get("bundles")
    entries: list[BundleCatalogEntry] = []
    if isinstance(bundles_raw, list):
        for b in bundles_raw:
            if not isinstance(b, dict) or b.get("id") is None:
                continue
            tags_raw = b.get("tags") or []
            tags = [str(t) for t in tags_raw if t is not None]
            entries.append(
                BundleCatalogEntry(
                    id=str(b["id"]).strip(),
                    title=str(b["title"]) if b.get("title") is not None else None,
                    tags=tags,
                ),
            )
    wmap = raw.get("workflow_bundle_map")
    workflow_map = (
        {str(k): str(v) for k, v in wmap.items() if v is not None} if isinstance(wmap, dict) else {}
    )
    ver = raw.get("version")
    version = int(ver) if ver is not None else None
    sync = bundle_faiss_index_sync_state(orch.repo_root)
    return BundleCatalogResponse(
        version=version,
        bundles=entries,
        workflow_bundle_map=workflow_map,
        faiss_index_ready=bundle_faiss_index_ready(orch.repo_root),
        faiss_index_stale=sync.get("stale"),
    )


def _hit_from_row(row: dict[str, Any]) -> BundleSearchHit | None:
    bid = row.get("id")
    if bid is None:
        return None
    title = row.get("title")
    raw_tags = row.get("tags") or []
    tags = [str(t) for t in raw_tags if t is not None]
    return BundleSearchHit(
        id=str(bid).strip(),
        title=str(title) if title is not None else None,
        tags=tags,
    )


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
        hit = _hit_from_row(row)
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


@router.get(
    "/catalog",
    response_model=BundleCatalogResponse,
    responses={503: PROBLEM_RESPONSE_503, 500: PROBLEM_RESPONSE_500},
    summary="Read bundle catalog metadata",
)
def get_bundle_catalog(orch: OrchDep) -> BundleCatalogResponse:
    return _catalog_response(orch, _load_catalog_raw(orch))


@router.get(
    "/catalog/source",
    summary="Bundle catalog authority metadata",
)
def get_bundle_catalog_source(orch: OrchDep) -> dict[str, Any]:
    mat = _config_materializer(orch)
    if mat is not None and getattr(mat, "use_db", False):
        return {
            "authoritative": "postgres",
            "document": "nimbusware_config_document",
            "namespace": "policy",
            "document_key": "bundle-catalog",
        }
    return {
        "authoritative": "yaml",
        "path": str(orch.repo_root / "configs" / "bundles" / "catalog.yaml"),
    }


@router.put(
    "/catalog",
    response_model=BundleCatalogResponse,
    responses={
        401: PROBLEM_RESPONSE_401,
        422: PROBLEM_RESPONSE_422,
        503: PROBLEM_RESPONSE_503,
        500: PROBLEM_RESPONSE_500,
    },
    summary="Replace bundle catalog (admin)",
)
def put_bundle_catalog(
    body: BundleCatalogPutRequest,
    orch: OrchDep,
    _admin: AdminDep,
) -> BundleCatalogResponse:
    content: dict[str, Any] = {
        "version": body.version if body.version is not None else 1,
        "bundles": [b.model_dump() for b in body.bundles],
        "workflow_bundle_map": dict(body.workflow_bundle_map),
    }
    try:
        validate_bundle_catalog_content(content)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("bundle_catalog_invalid", str(exc)),
        ) from exc
    persist_bundle_catalog_dict(
        orch.repo_root,
        content,
        materializer=_config_materializer(orch),
    )
    mat = _config_materializer(orch)
    if mat is not None and hasattr(mat, "refresh"):
        mat.refresh()
    return _catalog_response(orch, content)


@router.patch(
    "/catalog/bundles/{bundle_id}",
    response_model=BundleCatalogResponse,
    responses={
        401: PROBLEM_RESPONSE_401,
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        503: PROBLEM_RESPONSE_503,
    },
    summary="Patch one bundle entry (admin)",
)
def patch_bundle_catalog_entry(
    bundle_id: str,
    body: BundleCatalogPatchRequest,
    orch: OrchDep,
    _admin: AdminDep,
) -> BundleCatalogResponse:
    raw = deepcopy(_load_catalog_raw(orch))
    bundles = raw.get("bundles")
    if not isinstance(bundles, list):
        bundles = []
        raw["bundles"] = bundles
    bid = bundle_id.strip()
    found: dict[str, Any] | None = None
    for b in bundles:
        if isinstance(b, dict) and str(b.get("id", "")).strip() == bid:
            found = b
            break
    if found is None:
        raise HTTPException(
            status_code=404,
            detail=problem("bundle_not_found", f"bundle id {bid!r} not in catalog"),
        )
    if body.title is not None:
        found["title"] = body.title
    if body.tags is not None:
        found["tags"] = list(body.tags)
    try:
        validate_bundle_catalog_content(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("bundle_catalog_invalid", str(exc)),
        ) from exc
    persist_bundle_catalog_dict(
        orch.repo_root,
        raw,
        materializer=_config_materializer(orch),
    )
    mat = _config_materializer(orch)
    if mat is not None and hasattr(mat, "refresh"):
        mat.refresh()
    return _catalog_response(orch, raw)
