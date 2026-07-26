from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

EmbeddingMode = Literal["deterministic", "ollama"]


class MemoryChunkRecord(BaseModel):
    model_config = {"frozen": True}

    chunk_id: UUID
    generation_id: UUID
    repo_scope_hash: str
    run_id: UUID
    source_event_type: str
    source_store_seq: int | None = None
    finding_id: UUID | None = None
    category: str | None = None
    severity: str | None = None
    excerpt: str
    embedding_model_id: str
    embedding_dim: int = Field(ge=1)
    embedding_vector: list[float]


class MemoryRetrievalHit(BaseModel):
    model_config = {"frozen": True}

    chunk_id: UUID
    excerpt: str
    score: float
    run_id: UUID
    category: str | None = None


@dataclass(frozen=True)
class MemoryChunkDraft:
    run_id: UUID
    source_event_type: str
    source_store_seq: int | None
    finding_id: UUID | None
    category: str | None
    severity: str | None
    excerpt: str
