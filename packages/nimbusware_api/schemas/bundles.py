"""Pydantic models for bundle catalog HTTP responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BundleSearchHit(BaseModel):
    id: str
    title: str | None = None
    tags: list[str] = Field(default_factory=list)


class BundleCatalogEntry(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    title: str | None = None
    tags: list[str] = Field(default_factory=list)


class BundleCatalogResponse(BaseModel):
    version: int | None = None
    bundles: list[BundleCatalogEntry] = Field(default_factory=list)
    workflow_bundle_map: dict[str, str] = Field(default_factory=dict)
    faiss_index_ready: bool = False
    faiss_index_stale: bool | None = None


class BundleCatalogPutRequest(BaseModel):
    version: int | None = None
    bundles: list[BundleCatalogEntry]
    workflow_bundle_map: dict[str, str] = Field(default_factory=dict)


class BundleCatalogPatchRequest(BaseModel):
    title: str | None = None
    tags: list[str] | None = None


class BundleSearchResponse(BaseModel):
    query: str
    k: int = Field(
        default=5,
        ge=1,
        le=20,
        description=(
            "Echoed bounded ``k`` (1..20) that the response was sized to. Matches the "
            "``k`` echoed by the Streamlit ``run_bundle_catalog_search`` payload so API "
            "and console clients can deduplicate hits consistently."
        ),
    )
    hits: list[BundleSearchHit]
    faiss_index_ready: bool = Field(
        default=False,
        description=(
            "True when both ``configs/bundles/index/faiss.index`` and "
            "``configs/bundles/index/bundle_order.json`` exist under the orchestrator "
            "repo root, signaling that ``search_bundles`` used the FAISS top-k path "
            "(rather than the tag/id fallback) for this response. Mirrors the console "
            "FAISS readiness caption."
        ),
    )
    faiss_index_stale: bool | None = Field(
        default=None,
        description=(
            "``True`` when both index files exist and ``configs/bundles/catalog.yaml`` is "
            "newer than the index files (rebuild recommended). ``False`` when both index "
            "files exist and the catalog is not newer. ``None`` when the index is incomplete "
            "or the catalog is missing — same semantics as ``bundle_faiss_index_sync_state`` "
            "``stale`` in ``hermes_extensions.catalog``."
        ),
    )
