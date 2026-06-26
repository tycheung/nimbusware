from __future__ import annotations

from nimbusware_memory.embeddings import ollama_embedding_available
from nimbusware_memory.models import EmbeddingMode


def resolve_fleet_embedding_mode(requested: str | None = None) -> EmbeddingMode:
    raw = str(requested or "").strip().lower()
    if raw in ("deterministic", "ollama"):
        return raw  # type: ignore[return-value]
    if ollama_embedding_available():
        return "ollama"
    return "deterministic"
