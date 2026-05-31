"""Fleet memory pull/push helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from hermes_memory.org_scope import resolve_fleet_scope
from hermes_memory.remote_store import (
    FileFleetMemoryCanonicalStore,
    bundle_from_store_rows,
    import_bundle_to_memory_store,
    resolve_canonical_store_root,
)
from hermes_memory.store import MemoryChunkStore


def push_fleet_memory_to_canonical(
    memory_store: MemoryChunkStore,
    *,
    canonical_root: Path | str | None = None,
    tenant_id: UUID | None = None,
    org_slug: str = "default",
) -> dict[str, Any]:
    tid, org_scope = resolve_fleet_scope(tenant_id=tenant_id, org_slug=org_slug)
    gen = memory_store.latest_generation(org_scope_hash=org_scope, tenant_id=tid)
    if gen is None:
        msg = f"no fleet memory generation for org_scope_hash={org_scope}"
        raise ValueError(msg)
    chunks = memory_store.list_chunks_for_org_scope(org_scope, tenant_id=tid)
    bundle = bundle_from_store_rows(
        tenant_id=tid,
        org_scope_hash=org_scope,
        generation_id=gen.generation_id,
        repo_scope_hash=gen.repo_scope_hash,
        embedding_mode=gen.embedding_mode,
        embedding_model_id=gen.embedding_model_id,
        chunks=chunks,
    )
    store = FileFleetMemoryCanonicalStore(resolve_canonical_store_root(canonical_root))
    dest = store.push(bundle)
    return {
        "org_scope_hash": org_scope,
        "generation_id": str(gen.generation_id),
        "chunk_count": len(chunks),
        "canonical_path": str(dest),
    }


def pull_fleet_memory_from_canonical(
    memory_store: MemoryChunkStore,
    *,
    canonical_root: Path | str | None = None,
    tenant_id: UUID | None = None,
    org_slug: str = "default",
    generation_id: str | None = None,
) -> dict[str, Any]:
    tid, org_scope = resolve_fleet_scope(tenant_id=tenant_id, org_slug=org_slug)
    store = FileFleetMemoryCanonicalStore(resolve_canonical_store_root(canonical_root))
    if generation_id:
        bundle = store.pull_generation(org_scope, generation_id)
    else:
        bundle = store.pull_latest(org_scope)
    if bundle is None:
        msg = f"no canonical bundle for org_scope_hash={org_scope}"
        raise ValueError(msg)
    if UUID(bundle.tenant_id) != tid:
        msg = "canonical bundle tenant_id does not match authenticated tenant"
        raise ValueError(msg)
    import_bundle_to_memory_store(memory_store, bundle, tenant_id=tid)
    return {
        "org_scope_hash": org_scope,
        "generation_id": bundle.generation_id,
        "chunk_count": bundle.chunk_count,
        "tenant_id": str(tid),
    }


def fleet_memory_remote_status(
    *,
    org_scope_hash: str,
    canonical_root: Path | str | None = None,
) -> dict[str, Any]:
    try:
        root = resolve_canonical_store_root(canonical_root)
    except ValueError as exc:
        return {"configured": False, "message": str(exc)}
    store = FileFleetMemoryCanonicalStore(root)
    latest = store.pull_latest(org_scope_hash)
    return {
        "configured": True,
        "canonical_root": str(root),
        "org_scope_hash": org_scope_hash,
        "latest_generation_id": latest.generation_id if latest else None,
        "latest_chunk_count": latest.chunk_count if latest else 0,
        "generations": store.list_generations(org_scope_hash),
    }
