from __future__ import annotations

from copy import deepcopy
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import OrchDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.bundles import (
    BundleCatalogCreateRequest,
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
from nimbusware_config.persist import (
    bundle_catalog_document_version,
    load_bundle_catalog_dict,
    persist_bundle_catalog_dict,
)
from nimbusware_extensions.catalog import (
    bundle_faiss_index_ready,
    bundle_faiss_index_sync_state,
    search_bundles,
    validate_bundle_catalog_content,
)

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


def _catalog_authority(orch: Any) -> str:
    mat = _config_materializer(orch)
    if mat is not None and getattr(mat, "use_db", False):
        return "postgres"
    return "yaml"


def _persist_catalog(
    orch: Any,
    content: dict[str, Any],
    *,
    expected_version: int,
) -> int:
    mat = _config_materializer(orch)
    try:
        new_ver = persist_bundle_catalog_dict(
            orch.repo_root,
            content,
            materializer=mat,
            expected_version=expected_version,
        )
    except ValueError as exc:
        if "version conflict" in str(exc).lower() or "config version conflict" in str(exc).lower():
            raise HTTPException(
                status_code=409,
                detail=problem("bundle_catalog_version_conflict", str(exc)),
            ) from exc
        raise HTTPException(
            status_code=422,
            detail=problem("bundle_catalog_invalid", str(exc)),
        ) from exc
    content["version"] = new_ver
    if mat is not None and hasattr(mat, "refresh"):
        mat.refresh()
    return new_ver


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
    doc_ver = int(raw.get("version") or 0) or bundle_catalog_document_version(
        orch.repo_root,
        materializer=_config_materializer(orch),
        raw=raw,
    )
    return BundleCatalogResponse(
        version=version,
        document_version=doc_ver,
        authoritative=_catalog_authority(orch),
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
    _persist_catalog(orch, content, expected_version=body.expected_version)
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
    _persist_catalog(orch, raw, expected_version=body.expected_version)
    return _catalog_response(orch, raw)


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
    raw = deepcopy(_load_catalog_raw(orch))
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
    _persist_catalog(orch, raw, expected_version=body.expected_version)
    return _catalog_response(orch, raw)


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
    raw = deepcopy(_load_catalog_raw(orch))
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
    _persist_catalog(orch, raw, expected_version=expected_version)
    return _catalog_response(orch, raw)


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
    from nimbusware_research.bundle_promotion import (
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
    raw = deepcopy(_load_catalog_raw(orch))
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
    _persist_catalog(orch, raw, expected_version=expected_version)
    mark_catalog_candidate_promoted(
        orch.repo_root,
        run_id=run_id,
        candidate_id=candidate_id,
    )
    return _catalog_response(orch, raw)


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
    from nimbusware_research.bundle_promotion import (
        candidate_to_bundle_entry,
        list_pending_stitch_catalog_candidates,
        load_catalog_candidate,
        mark_catalog_candidate_promoted,
    )

    pending = list_pending_stitch_catalog_candidates(orch.repo_root, limit=500)
    if not pending:
        return _catalog_response(orch, _load_catalog_raw(orch))
    raw = deepcopy(_load_catalog_raw(orch))
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
        return _catalog_response(orch, raw)
    try:
        validate_bundle_catalog_content(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("bundle_catalog_invalid", str(exc)),
        ) from exc
    _persist_catalog(orch, raw, expected_version=expected_version)
    for row in pending:
        run_id = str(row.get("run_id") or "").strip()
        candidate_id = str(row.get("candidate_id") or "").strip()
        if candidate_id in promoted and run_id:
            mark_catalog_candidate_promoted(
                orch.repo_root,
                run_id=run_id,
                candidate_id=candidate_id,
            )
    return _catalog_response(orch, raw)


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
    from nimbusware_research.bundle_promotion import list_catalog_candidates

    return {"candidates": list_catalog_candidates(orch.repo_root, limit=limit)}
