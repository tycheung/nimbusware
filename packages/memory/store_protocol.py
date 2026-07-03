from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from iam.context import resolve_store_tenant_id
from memory.models import EmbeddingMode, MemoryChunkRecord


@dataclass(frozen=True)
class IndexGenerationRow:
    generation_id: UUID
    tenant_id: UUID
    org_scope_hash: str
    repo_scope_hash: str
    embedding_mode: EmbeddingMode
    embedding_model_id: str
    chunk_count: int
    manifest_relpath: str | None
    created_at: datetime | None = None


@runtime_checkable
class MemoryChunkStore(Protocol):
    def replace_generation(
        self,
        *,
        generation_id: UUID | None = None,
        tenant_id: UUID | None = None,
        org_scope_hash: str,
        repo_scope_hash: str,
        embedding_mode: EmbeddingMode,
        embedding_model_id: str,
        chunks: list[MemoryChunkRecord],
        manifest_relpath: str | None,
    ) -> IndexGenerationRow: ...

    def list_chunks_for_scope(self, repo_scope_hash: str) -> list[MemoryChunkRecord]: ...

    def list_chunks_for_org_scope(
        self,
        org_scope_hash: str,
        *,
        tenant_id: UUID | None = None,
    ) -> list[MemoryChunkRecord]: ...

    def latest_generation(
        self,
        repo_scope_hash: str | None = None,
        *,
        org_scope_hash: str | None = None,
        tenant_id: UUID | None = None,
    ) -> IndexGenerationRow | None: ...


def _resolve_tenant(tenant_id: UUID | None) -> UUID:
    return tenant_id or resolve_store_tenant_id()
