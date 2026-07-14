from __future__ import annotations

from copy import deepcopy
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from api.admin import AdminDep
from api.deps import OrchDep
from api.errors import problem
from api.routes import bundles_search
from api.routes.bundles_helpers import (
    catalog_response,
    config_materializer,
    load_catalog_raw,
    persist_catalog,
)
from api.schemas.bundles import (
    BundleCatalogCreateRequest,
    BundleCatalogPatchRequest,
    BundleCatalogPutRequest,
    BundleCatalogResponse,
)
from api.schemas.openapi import (
    PROBLEM_RESPONSE_401,
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
    PROBLEM_RESPONSE_503,
)
from extensions.catalog import validate_bundle_catalog_content

router = APIRouter(prefix="/bundles", tags=["bundles"])
router.include_router(bundles_search.router)


@router.get(
    "/catalog",
    response_model=BundleCatalogResponse,
    responses={503: PROBLEM_RESPONSE_503, 500: PROBLEM_RESPONSE_500},
    summary="Read bundle catalog metadata",
)
def get_bundle_catalog(orch: OrchDep) -> BundleCatalogResponse:
    return catalog_response(orch, load_catalog_raw(orch))


@router.get(
    "/catalog/source",
    summary="Bundle catalog authority metadata",
)
def get_bundle_catalog_source(orch: OrchDep) -> dict[str, Any]:
    mat = config_materializer(orch)
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
    persist_catalog(orch, content, expected_version=body.expected_version)
    return catalog_response(orch, content)


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
    raw = deepcopy(load_catalog_raw(orch))
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
    persist_catalog(orch, raw, expected_version=body.expected_version)
    return catalog_response(orch, raw)


@router.post(
    "/catalog/bundles",
    response_model=BundleCatalogResponse,
    responses={
        401: PROBLEM_RESPONSE_401,
        409: PROBLEM_RESPONSE_422,
        422: PROBLEM_RESPONSE_422,
        503: PROBLEM_RESPONSE_503,
    },
    summary="Append one bundle entry (admin)",
)
def post_bundle_catalog_entry(
    body: BundleCatalogCreateRequest,
    orch: OrchDep,
    _admin: AdminDep,
) -> BundleCatalogResponse:
    raw = deepcopy(load_catalog_raw(orch))
    bundles = raw.get("bundles")
    if not isinstance(bundles, list):
        bundles = []
        raw["bundles"] = bundles
    bid = body.entry.id.strip()
    for b in bundles:
        if isinstance(b, dict) and str(b.get("id", "")).strip() == bid:
            raise HTTPException(
                status_code=409,
                detail=problem("bundle_exists", f"bundle id {bid!r} already in catalog"),
            )
    bundles.append(body.entry.model_dump())
    try:
        validate_bundle_catalog_content(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("bundle_catalog_invalid", str(exc)),
        ) from exc
    persist_catalog(orch, raw, expected_version=body.expected_version)
    return catalog_response(orch, raw)


@router.delete(
    "/catalog/bundles/{bundle_id}",
    response_model=BundleCatalogResponse,
    responses={
        401: PROBLEM_RESPONSE_401,
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        503: PROBLEM_RESPONSE_503,
    },
    summary="Remove one bundle entry (admin)",
)
def delete_bundle_catalog_entry(
    bundle_id: str,
    orch: OrchDep,
    _admin: AdminDep,
    expected_version: Annotated[int, Query(ge=1)],
) -> BundleCatalogResponse:
    raw = deepcopy(load_catalog_raw(orch))
    bundles = raw.get("bundles")
    if not isinstance(bundles, list):
        bundles = []
    bid = bundle_id.strip()
    new_bundles = [
        b for b in bundles if not (isinstance(b, dict) and str(b.get("id", "")).strip() == bid)
    ]
    if len(new_bundles) == len(bundles):
        raise HTTPException(
            status_code=404,
            detail=problem("bundle_not_found", f"bundle id {bid!r} not in catalog"),
        )
    raw["bundles"] = new_bundles
    wmap = raw.get("workflow_bundle_map")
    if isinstance(wmap, dict):
        raw["workflow_bundle_map"] = {
            str(k): str(v) for k, v in wmap.items() if v is not None and str(v).strip() != bid
        }
    try:
        validate_bundle_catalog_content(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("bundle_catalog_invalid", str(exc)),
        ) from exc
    persist_catalog(orch, raw, expected_version=expected_version)
    return catalog_response(orch, raw)


@router.post(
    "/catalog-candidates/{run_id}/{candidate_id}/promote",
    response_model=BundleCatalogResponse,
    responses={
        401: PROBLEM_RESPONSE_401,
        404: PROBLEM_RESPONSE_404,
        409: PROBLEM_RESPONSE_422,
        422: PROBLEM_RESPONSE_422,
    },
    summary="Promote a catalog candidate into the bundle catalog (admin)",
)
def promote_bundle_catalog_candidate(
    run_id: str,
    candidate_id: str,
    orch: OrchDep,
    _admin: AdminDep,
    expected_version: Annotated[int, Query(ge=1)],
) -> BundleCatalogResponse:
    from research.bundle_promotion import (
        candidate_to_bundle_entry,
        load_catalog_candidate,
        mark_catalog_candidate_promoted,
    )

    try:
        candidate = load_catalog_candidate(
            orch.repo_root,
            run_id=run_id,
            candidate_id=candidate_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=problem("catalog_candidate_not_found", str(exc)),
        ) from exc
    try:
        entry = candidate_to_bundle_entry(candidate)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("catalog_candidate_invalid", str(exc)),
        ) from exc
    raw = deepcopy(load_catalog_raw(orch))
    bundles = raw.get("bundles")
    if not isinstance(bundles, list):
        bundles = []
        raw["bundles"] = bundles
    bid = str(entry["id"]).strip()
    for b in bundles:
        if isinstance(b, dict) and str(b.get("id", "")).strip() == bid:
            raise HTTPException(
                status_code=409,
                detail=problem("bundle_exists", f"bundle id {bid!r} already in catalog"),
            )
    bundles.append(entry)
    try:
        validate_bundle_catalog_content(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("bundle_catalog_invalid", str(exc)),
        ) from exc
    persist_catalog(orch, raw, expected_version=expected_version)
    mark_catalog_candidate_promoted(
        orch.repo_root,
        run_id=run_id,
        candidate_id=candidate_id,
    )
    return catalog_response(orch, raw)


@router.post(
    "/catalog-candidates/promote-stitch-pending",
    response_model=BundleCatalogResponse,
    responses={
        401: PROBLEM_RESPONSE_401,
        409: PROBLEM_RESPONSE_422,
        422: PROBLEM_RESPONSE_422,
    },
    summary="Promote all pending stitch catalog candidates into the bundle catalog (admin)",
)
def promote_pending_stitch_catalog_candidates(
    orch: OrchDep,
    _admin: AdminDep,
    expected_version: Annotated[int, Query(ge=1)],
) -> BundleCatalogResponse:
    from research.bundle_promotion import (
        candidate_to_bundle_entry,
        list_pending_stitch_catalog_candidates,
        load_catalog_candidate,
        mark_catalog_candidate_promoted,
    )

    pending = list_pending_stitch_catalog_candidates(orch.repo_root, limit=500)
    if not pending:
        return catalog_response(orch, load_catalog_raw(orch))
    raw = deepcopy(load_catalog_raw(orch))
    bundles = raw.get("bundles")
    if not isinstance(bundles, list):
        bundles = []
        raw["bundles"] = bundles
    existing_ids = {str(b.get("id", "")).strip() for b in bundles if isinstance(b, dict)}
    promoted: list[str] = []
    for row in pending:
        run_id = str(row.get("run_id") or "").strip()
        candidate_id = str(row.get("candidate_id") or "").strip()
        if not run_id or not candidate_id:
            continue
        candidate = load_catalog_candidate(
            orch.repo_root,
            run_id=run_id,
            candidate_id=candidate_id,
        )
        entry = candidate_to_bundle_entry(candidate)
        bid = str(entry["id"]).strip()
        if bid in existing_ids:
            continue
        bundles.append(entry)
        existing_ids.add(bid)
        promoted.append(candidate_id)
    if not promoted:
        return catalog_response(orch, raw)
    try:
        validate_bundle_catalog_content(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("bundle_catalog_invalid", str(exc)),
        ) from exc
    persist_catalog(orch, raw, expected_version=expected_version)
    for row in pending:
        run_id = str(row.get("run_id") or "").strip()
        candidate_id = str(row.get("candidate_id") or "").strip()
        if candidate_id in promoted and run_id:
            mark_catalog_candidate_promoted(
                orch.repo_root,
                run_id=run_id,
                candidate_id=candidate_id,
            )
    return catalog_response(orch, raw)


@router.get(
    "/catalog-candidates",
    summary="List Code Researcher catalog promotion candidates (admin)",
    responses={401: PROBLEM_RESPONSE_401},
)
def list_bundle_catalog_candidates(
    orch: OrchDep,
    _admin: AdminDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    from research.bundle_promotion import list_catalog_candidates

    return {"candidates": list_catalog_candidates(orch.repo_root, limit=limit)}
