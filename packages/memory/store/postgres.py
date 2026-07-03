from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from memory.index.models import EmbeddingMode, MemoryChunkRecord
from memory.store.protocol import IndexGenerationRow, _resolve_tenant


class PostgresMemoryChunkStore:
    def __init__(self, conninfo: str) -> None:

        self._conninfo = conninfo

    @contextmanager
    def _connect(self) -> Iterator[psycopg.Connection[Any]]:

        tid = str(_resolve_tenant(None))

        with psycopg.connect(self._conninfo) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT set_config('nimbusware.tenant_id', %s, true)", (tid,))

            yield conn

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

        gen_id = generation_id or uuid4()

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """

                    DELETE FROM memory_chunk

                    WHERE tenant_id = %s AND org_scope_hash = %s

                    """,
                    (tid, org_scope_hash),
                )

                cur.execute(
                    """

                    DELETE FROM memory_index_generation

                    WHERE tenant_id = %s AND org_scope_hash = %s

                    """,
                    (tid, org_scope_hash),
                )

                cur.execute(
                    """

                    INSERT INTO memory_index_generation (

                      generation_id, tenant_id, org_scope_hash, repo_scope_hash,

                      embedding_mode, embedding_model_id, chunk_count, manifest_relpath

                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)

                    """,
                    (
                        gen_id,
                        tid,
                        org_scope_hash,
                        repo_scope_hash,
                        embedding_mode,
                        embedding_model_id,
                        len(chunks),
                        manifest_relpath,
                    ),
                )

                for ch in chunks:
                    cur.execute(
                        """

                        INSERT INTO memory_chunk (

                          chunk_id, generation_id, tenant_id, org_scope_hash, repo_scope_hash,

                          run_id, source_event_type, source_store_seq, finding_id,

                          category, severity, excerpt, embedding_model_id,

                          embedding_dim, embedding_vector

                        ) VALUES (

                          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s

                        )

                        """,
                        (
                            ch.chunk_id,
                            ch.generation_id,
                            tid,
                            org_scope_hash,
                            ch.repo_scope_hash,
                            ch.run_id,
                            ch.source_event_type,
                            ch.source_store_seq,
                            ch.finding_id,
                            ch.category,
                            ch.severity,
                            ch.excerpt,
                            ch.embedding_model_id,
                            ch.embedding_dim,
                            Jsonb(ch.embedding_vector),
                        ),
                    )

            conn.commit()

        return IndexGenerationRow(
            generation_id=gen_id,
            tenant_id=tid,
            org_scope_hash=org_scope_hash,
            repo_scope_hash=repo_scope_hash,
            embedding_mode=embedding_mode,
            embedding_model_id=embedding_model_id,
            chunk_count=len(chunks),
            manifest_relpath=manifest_relpath,
        )

    def list_chunks_for_scope(self, repo_scope_hash: str) -> list[MemoryChunkRecord]:

        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """

                    SELECT chunk_id, generation_id, repo_scope_hash, run_id,

                           source_event_type, source_store_seq, finding_id,

                           category, severity, excerpt, embedding_model_id,

                           embedding_dim, embedding_vector

                    FROM memory_chunk

                    WHERE repo_scope_hash = %s

                    ORDER BY created_at ASC

                    """,
                    (repo_scope_hash,),
                )

                recs = cur.fetchall()

        return [_chunk_from_row(r) for r in recs]

    def list_chunks_for_org_scope(
        self,
        org_scope_hash: str,
        *,
        tenant_id: UUID | None = None,
    ) -> list[MemoryChunkRecord]:

        tid = _resolve_tenant(tenant_id)

        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """

                    SELECT chunk_id, generation_id, repo_scope_hash, run_id,

                           source_event_type, source_store_seq, finding_id,

                           category, severity, excerpt, embedding_model_id,

                           embedding_dim, embedding_vector

                    FROM memory_chunk

                    WHERE tenant_id = %s AND org_scope_hash = %s

                    ORDER BY created_at ASC

                    """,
                    (tid, org_scope_hash),
                )

                recs = cur.fetchall()

        return [_chunk_from_row(r) for r in recs]

    def latest_generation(
        self,
        repo_scope_hash: str | None = None,
        *,
        org_scope_hash: str | None = None,
        tenant_id: UUID | None = None,
    ) -> IndexGenerationRow | None:

        tid = _resolve_tenant(tenant_id)

        clause = "tenant_id = %s"

        params: list[Any] = [tid]

        if org_scope_hash is not None:
            clause += " AND org_scope_hash = %s"

            params.append(org_scope_hash)

        elif repo_scope_hash is not None:
            clause += " AND repo_scope_hash = %s"

            params.append(repo_scope_hash)

        with self._connect() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""

                    SELECT generation_id, tenant_id, org_scope_hash, repo_scope_hash,

                           embedding_mode, embedding_model_id, chunk_count,

                           manifest_relpath, created_at

                    FROM memory_index_generation

                    WHERE {clause}

                    ORDER BY created_at DESC

                    LIMIT 1

                    """,
                    tuple(params),
                )

                rec = cur.fetchone()

        if rec is None:
            return None

        return IndexGenerationRow(
            generation_id=UUID(str(rec["generation_id"])),
            tenant_id=UUID(str(rec["tenant_id"])),
            org_scope_hash=str(rec["org_scope_hash"]),
            repo_scope_hash=str(rec["repo_scope_hash"]),
            embedding_mode=str(rec["embedding_mode"]),  # type: ignore[arg-type]
            embedding_model_id=str(rec["embedding_model_id"]),
            chunk_count=int(rec["chunk_count"]),
            manifest_relpath=rec.get("manifest_relpath"),
            created_at=rec.get("created_at"),
        )


def _chunk_from_row(rec: dict[str, Any]) -> MemoryChunkRecord:

    vec = rec["embedding_vector"]

    if not isinstance(vec, list):
        vec = []

    return MemoryChunkRecord(
        chunk_id=UUID(str(rec["chunk_id"])),
        generation_id=UUID(str(rec["generation_id"])),
        repo_scope_hash=str(rec["repo_scope_hash"]),
        run_id=UUID(str(rec["run_id"])),
        source_event_type=str(rec["source_event_type"]),
        source_store_seq=int(rec["source_store_seq"])
        if rec.get("source_store_seq") is not None
        else None,
        finding_id=UUID(str(rec["finding_id"])) if rec.get("finding_id") else None,
        category=rec.get("category"),
        severity=rec.get("severity"),
        excerpt=str(rec["excerpt"]),
        embedding_model_id=str(rec["embedding_model_id"]),
        embedding_dim=int(rec["embedding_dim"]),
        embedding_vector=[float(x) for x in vec],
    )
