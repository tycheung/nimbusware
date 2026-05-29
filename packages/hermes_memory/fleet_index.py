"""Fleet-scoped memory index rebuild (Lane D / fo202)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from hermes_memory.chunking import chunks_from_event_rows
from hermes_memory.embeddings import embed_text, embedding_model_id_for_mode
from hermes_memory.event_scan import fetch_event_rows_for_memory_index
from hermes_memory.faiss_index import build_memory_faiss_index
from hermes_memory.indexer import RebuildIndexResult, _drafts_to_records
from hermes_memory.manifest import MemoryIndexManifest, write_manifest
from hermes_memory.models import EmbeddingMode
from hermes_memory.org_scope import resolve_fleet_scope
from hermes_memory.repo_scope import repo_scope_hash, resolve_repo_root
from hermes_memory.store import MemoryChunkStore


def default_fleet_memory_index_dir(repo_root: Path, org_scope_hash: str) -> Path:
    return (repo_root / "configs" / "memory" / "fleet" / org_scope_hash).resolve()


@dataclass(frozen=True)
class FleetRebuildResult(RebuildIndexResult):
    tenant_id: UUID
    org_scope_hash: str


def rebuild_fleet_memory_index(
    memory_store: MemoryChunkStore,
    *,
    repo_root: Path | None = None,
    tenant_id: UUID | None = None,
    org_slug: str = "default",
    embedding_mode: EmbeddingMode = "deterministic",
    conninfo: str | None = None,
    in_memory_event_rows: list[dict[str, Any]] | None = None,
    audit_store: Any | None = None,
    audit_run_id: UUID | None = None,
) -> FleetRebuildResult:
    """Rebuild tenant fleet index from tenant-scoped events (Enterprise only)."""
    tid, org_scope = resolve_fleet_scope(tenant_id=tenant_id, org_slug=org_slug)
    root = resolve_repo_root(repo_root)
    repo_scope = repo_scope_hash(root)
    model_id = embedding_model_id_for_mode(embedding_mode)
    rows = fetch_event_rows_for_memory_index(
        conninfo=conninfo,
        in_memory_rows=in_memory_event_rows,
        tenant_scoped=True,
    )
    drafts = chunks_from_event_rows(rows)
    gen_id = uuid4()
    records, skipped = _drafts_to_records(
        drafts,
        generation_id=gen_id,
        scope=repo_scope,
        mode=embedding_mode,
        model_id=model_id,
    )
    index_dir = default_fleet_memory_index_dir(root, org_scope)
    manifest_relpath = (
        str(index_dir.relative_to(root)) if index_dir.is_relative_to(root) else str(index_dir)
    )
    gen_row = memory_store.replace_generation(
        generation_id=gen_id,
        tenant_id=tid,
        org_scope_hash=org_scope,
        repo_scope_hash=repo_scope,
        embedding_mode=embedding_mode,
        embedding_model_id=model_id,
        chunks=records,
        manifest_relpath=manifest_relpath,
    )
    manifest = MemoryIndexManifest(
        generation_id=str(gen_row.generation_id),
        repo_scope_hash=repo_scope,
        org_scope_hash=org_scope,
        tenant_id=str(tid),
        embedding_mode=embedding_mode,
        embedding_model_id=model_id,
        chunk_count=len(records),
        built_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    manifest_path = write_manifest(index_dir, manifest)
    build_memory_faiss_index(chunks=records, index_dir=index_dir)
    result = FleetRebuildResult(
        generation_id=gen_row.generation_id,
        repo_scope_hash=repo_scope,
        tenant_id=tid,
        org_scope_hash=org_scope,
        chunks_added=len(records),
        chunks_skipped=skipped,
        embedding_mode=embedding_mode,
        embedding_model_id=model_id,
        manifest_path=manifest_path,
    )
    if audit_store is not None and audit_run_id is not None:
        from hermes_memory.audit import append_memory_indexed_event

        append_memory_indexed_event(audit_store, run_id=audit_run_id, result=result)
    return result
