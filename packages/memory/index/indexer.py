from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from memory.event_scan import fetch_event_rows_for_memory_index
from memory.index.chunking import chunks_from_event_rows
from memory.index.embeddings import embed_text, embedding_model_id_for_mode
from memory.index.faiss_index import build_memory_faiss_index
from memory.index.fingerprint import memory_event_rows_fingerprint
from memory.index.manifest import (
    MemoryIndexManifest,
    default_memory_index_dir,
    read_manifest,
    write_manifest,
)
from memory.index.models import EmbeddingMode, MemoryChunkRecord
from memory.index.repo_scope import repo_scope_hash, resolve_repo_root
from memory.store.protocol import MemoryChunkStore

_CHUNK_ID_NAMESPACE = UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479")


def deterministic_chunk_id(
    *,
    repo_scope_hash: str,
    run_id: UUID,
    source_event_type: str,
    source_store_seq: int | None,
    excerpt: str,
) -> UUID:
    key = f"{repo_scope_hash}|{run_id}|{source_event_type}|{source_store_seq}|{excerpt.strip()}"
    return uuid5(NAMESPACE_URL, key)


@dataclass(frozen=True)
class RebuildIndexResult:
    generation_id: UUID
    repo_scope_hash: str
    chunks_added: int
    chunks_skipped: int
    embedding_mode: EmbeddingMode
    embedding_model_id: str
    manifest_path: Path
    rebuild_skipped: bool


def _drafts_to_records(
    drafts: list[Any],
    *,
    generation_id: UUID,
    scope: str,
    mode: EmbeddingMode,
    model_id: str,
) -> tuple[list[MemoryChunkRecord], int]:
    records: list[MemoryChunkRecord] = []
    skipped = 0
    for draft in drafts:
        text = (draft.excerpt or "").strip()
        if not text:
            skipped += 1
            continue
        vec = embed_text(text, mode=mode)
        records.append(
            MemoryChunkRecord(
                chunk_id=deterministic_chunk_id(
                    repo_scope_hash=scope,
                    run_id=draft.run_id,
                    source_event_type=draft.source_event_type,
                    source_store_seq=draft.source_store_seq,
                    excerpt=text,
                ),
                generation_id=generation_id,
                repo_scope_hash=scope,
                run_id=draft.run_id,
                source_event_type=draft.source_event_type,
                source_store_seq=draft.source_store_seq,
                finding_id=draft.finding_id,
                category=draft.category,
                severity=draft.severity,
                excerpt=text,
                embedding_model_id=model_id,
                embedding_dim=len(vec),
                embedding_vector=vec,
            ),
        )
    return records, skipped


def rebuild_memory_index(
    memory_store: MemoryChunkStore,
    *,
    repo_root: Path | None = None,
    embedding_mode: EmbeddingMode = "deterministic",
    conninfo: str | None = None,
    in_memory_event_rows: list[dict[str, Any]] | None = None,
    audit_store: Any | None = None,
    audit_run_id: UUID | None = None,
) -> RebuildIndexResult:
    root = resolve_repo_root(repo_root)
    scope = repo_scope_hash(root)
    model_id = embedding_model_id_for_mode(embedding_mode)
    rows = fetch_event_rows_for_memory_index(
        conninfo=conninfo,
        in_memory_rows=in_memory_event_rows,
    )
    fingerprint = memory_event_rows_fingerprint(rows)
    max_seq = max((int(r.get("store_seq") or 0) for r in rows), default=0)
    index_dir = default_memory_index_dir(root)
    existing = read_manifest(index_dir)
    if (
        existing is not None
        and existing.repo_scope_hash == scope
        and existing.embedding_mode == embedding_mode
        and existing.embedding_model_id == model_id
        and existing.source_events_fingerprint == fingerprint
    ):
        try:
            gen_id = UUID(existing.generation_id)
        except ValueError:
            gen_id = uuid4()
        return RebuildIndexResult(
            generation_id=gen_id,
            repo_scope_hash=scope,
            chunks_added=existing.chunk_count,
            chunks_skipped=0,
            embedding_mode=embedding_mode,
            embedding_model_id=model_id,
            manifest_path=index_dir / "manifest.json",
            rebuild_skipped=True,
        )
    drafts = chunks_from_event_rows(rows)
    gen_id = uuid4()
    records, skipped = _drafts_to_records(
        drafts,
        generation_id=gen_id,
        scope=scope,
        mode=embedding_mode,
        model_id=model_id,
    )
    manifest_relpath = (
        str(index_dir.relative_to(root))
        if index_dir.is_relative_to(root)
        else str(
            index_dir,
        )
    )
    gen_row = memory_store.replace_generation(
        generation_id=gen_id,
        org_scope_hash=scope,
        repo_scope_hash=scope,
        embedding_mode=embedding_mode,
        embedding_model_id=model_id,
        chunks=records,
        manifest_relpath=manifest_relpath,
    )
    manifest = MemoryIndexManifest(
        generation_id=str(gen_row.generation_id),
        repo_scope_hash=scope,
        embedding_mode=embedding_mode,
        embedding_model_id=model_id,
        chunk_count=len(records),
        built_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        source_events_fingerprint=fingerprint,
        source_max_store_seq=max_seq,
    )
    manifest_path = write_manifest(index_dir, manifest)
    build_memory_faiss_index(chunks=records, index_dir=index_dir)
    result = RebuildIndexResult(
        generation_id=gen_row.generation_id,
        repo_scope_hash=scope,
        chunks_added=len(records),
        chunks_skipped=skipped,
        embedding_mode=embedding_mode,
        embedding_model_id=model_id,
        manifest_path=manifest_path,
        rebuild_skipped=False,
    )
    if audit_store is not None and audit_run_id is not None:
        from memory.index.audit import append_memory_indexed_event

        append_memory_indexed_event(audit_store, run_id=audit_run_id, result=result)
    return result
