from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from agent_core.mapping import mapping_or_empty
from nimbusware_api.errors import problem
from nimbusware_api.schemas.bundles import (
    BundleCatalogEntry,
    BundleCatalogResponse,
    BundleSearchHit,
)
from nimbusware_config.persist import (
    bundle_catalog_document_version,
    load_bundle_catalog_dict,
    persist_bundle_catalog_dict,
)
from nimbusware_extensions.catalog import (
    bundle_faiss_index_ready,
    bundle_faiss_index_sync_state,
)


def config_materializer(orch: Any) -> Any | None:
    return getattr(orch, "config_materializer", None)


def load_catalog_raw(orch: Any) -> dict[str, Any]:
    mat = config_materializer(orch)
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
    if not mapping_or_empty(raw):
        raise HTTPException(
            status_code=500,
            detail=problem("bundle_catalog_invalid", "bundle catalog must be a mapping"),
        )
    return raw


def catalog_authority(orch: Any) -> str:
    mat = config_materializer(orch)
    if mat is not None and getattr(mat, "use_db", False):
        return "postgres"
    return "yaml"


def persist_catalog(
    orch: Any,
    content: dict[str, Any],
    *,
    expected_version: int,
) -> int:
    mat = config_materializer(orch)
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


def catalog_response(orch: Any, raw: dict[str, Any]) -> BundleCatalogResponse:
    bundles_raw = raw.get("bundles")
    entries: list[BundleCatalogEntry] = []
    if isinstance(bundles_raw, list):
        for b in bundles_raw:
            row = mapping_or_empty(b)
            if not row or row.get("id") is None:
                continue
            tags_raw = row.get("tags") or []
            tags = [str(t) for t in tags_raw if t is not None]
            entries.append(
                BundleCatalogEntry(
                    id=str(row["id"]).strip(),
                    title=str(row["title"]) if row.get("title") is not None else None,
                    tags=tags,
                ),
            )
    wmap = mapping_or_empty(raw.get("workflow_bundle_map"))
    workflow_map = {str(k): str(v) for k, v in wmap.items() if v is not None}
    ver = raw.get("version")
    version = int(ver) if ver is not None else None
    sync = bundle_faiss_index_sync_state(orch.repo_root)
    doc_ver = int(raw.get("version") or 0) or bundle_catalog_document_version(
        orch.repo_root,
        materializer=config_materializer(orch),
        raw=raw,
    )
    return BundleCatalogResponse(
        version=version,
        document_version=doc_ver,
        authoritative=catalog_authority(orch),
        bundles=entries,
        workflow_bundle_map=workflow_map,
        faiss_index_ready=bundle_faiss_index_ready(orch.repo_root),
        faiss_index_stale=sync.get("stale"),
    )


def hit_from_row(row: dict[str, Any]) -> BundleSearchHit | None:
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
