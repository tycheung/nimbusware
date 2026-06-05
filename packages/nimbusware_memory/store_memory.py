"""In-memory memory chunk store (tests)."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from nimbusware_memory.models import EmbeddingMode, MemoryChunkRecord
from nimbusware_memory.store_protocol import IndexGenerationRow, _resolve_tenant


class InMemoryMemoryChunkStore:
    """Test double for memory chunk tables."""

    def __init__(self) -> None:

        self.generations: list[IndexGenerationRow] = []

        self.chunks: list[MemoryChunkRecord] = []

        self._chunk_tenant: dict[UUID, UUID] = {}

        self._chunk_org_scope: dict[UUID, str] = {}

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
    ) -> IndexGenerationRow:

        tid = _resolve_tenant(tenant_id)

        self.chunks = [
            c
            for c in self.chunks
            if self._chunk_org_scope.get(c.chunk_id) != org_scope_hash
            or self._chunk_tenant.get(c.chunk_id) != tid
        ]

        self.generations = [
            g
            for g in self.generations
            if not (g.tenant_id == tid and g.org_scope_hash == org_scope_hash)
        ]

        gen_id = generation_id or uuid4()

        row = IndexGenerationRow(
            generation_id=gen_id,
            tenant_id=tid,
            org_scope_hash=org_scope_hash,
            repo_scope_hash=repo_scope_hash,
            embedding_mode=embedding_mode,
            embedding_model_id=embedding_model_id,
            chunk_count=len(chunks),
            manifest_relpath=manifest_relpath,
            created_at=datetime.now(timezone.utc),
        )

        self.generations.append(row)

        for ch in chunks:
            self.chunks.append(ch)

            self._chunk_tenant[ch.chunk_id] = tid

            self._chunk_org_scope[ch.chunk_id] = org_scope_hash

        return row

    def list_chunks_for_scope(self, repo_scope_hash: str) -> list[MemoryChunkRecord]:

        return [c for c in self.chunks if c.repo_scope_hash == repo_scope_hash]

    def list_chunks_for_org_scope(
        self,
        org_scope_hash: str,
        *,
        tenant_id: UUID | None = None,
    ) -> list[MemoryChunkRecord]:

        tid = _resolve_tenant(tenant_id)

        return [
            c
            for c in self.chunks
            if self._chunk_org_scope.get(c.chunk_id) == org_scope_hash
            and self._chunk_tenant.get(c.chunk_id) == tid
        ]

    def latest_generation(
        self,
        repo_scope_hash: str | None = None,
        *,
        org_scope_hash: str | None = None,
        tenant_id: UUID | None = None,
    ) -> IndexGenerationRow | None:

        tid = _resolve_tenant(tenant_id)

        rows = [g for g in self.generations if g.tenant_id == tid]

        if org_scope_hash is not None:
            rows = [g for g in rows if g.org_scope_hash == org_scope_hash]

        elif repo_scope_hash is not None:
            rows = [g for g in rows if g.repo_scope_hash == repo_scope_hash]

        return rows[-1] if rows else None
