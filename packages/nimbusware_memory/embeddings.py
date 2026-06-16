from __future__ import annotations

import hashlib

import httpx
import numpy as np
from numpy.typing import NDArray

from nimbusware_env.env_flags import (
    nimbusware_memory_embedding_model,
    nimbusware_use_llm_enabled,
)
from nimbusware_memory.models import EmbeddingMode

_DETERMINISTIC_DIM = 32
_DETERMINISTIC_MODEL_ID = "nimbusware-memory-deterministic-v1"
_DEFAULT_OLLAMA_EMBED_MODEL = "nomic-embed-text"


def embedding_model_id_for_mode(
    mode: EmbeddingMode,
    *,
    ollama_model: str | None = None,
) -> str:
    if mode == "ollama":
        model = (ollama_model or _default_ollama_embedding_model()).strip()
        return f"ollama:{model}" if model else "ollama-embedding-pending"
    return _DETERMINISTIC_MODEL_ID


def _default_ollama_embedding_model() -> str:
    env = nimbusware_memory_embedding_model()
    if env:
        return env
    return _DEFAULT_OLLAMA_EMBED_MODEL


def _ollama_runtime_from_env() -> tuple[str, str]:
    from nimbusware_env.env_flags import nimbusware_ollama_base_url

    return nimbusware_ollama_base_url(), _default_ollama_embedding_model()


def deterministic_embed(text: str, *, dim: int = _DETERMINISTIC_DIM) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    need = dim * 4
    buf = (digest * ((need // len(digest)) + 1))[:need]
    vec: NDArray[np.float32] = np.frombuffer(buf, dtype=np.uint8).astype(np.float32)
    if vec.size > dim:
        vec = vec[:dim]
    norm = float(np.linalg.norm(vec)) + 1e-9
    return [float(x) for x in (vec / norm).tolist()]


def ollama_embed(
    text: str,
    *,
    base_url: str | None = None,
    model: str | None = None,
    timeout_seconds: float = 60.0,
) -> list[float]:
    url_base, default_model = _ollama_runtime_from_env()
    endpoint = (base_url or url_base).rstrip("/") + "/api/embeddings"
    embed_model = (model or default_model).strip()
    response = httpx.post(
        endpoint,
        json={"model": embed_model, "prompt": text},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    raw = payload.get("embedding") if isinstance(payload, dict) else None
    if not isinstance(raw, list) or not raw:
        msg = "missing embedding vector in Ollama response"
        raise ValueError(msg)
    vec = np.asarray(raw, dtype=np.float32)
    norm = float(np.linalg.norm(vec)) + 1e-9
    return [float(x) for x in (vec / norm).tolist()]


def ollama_embedding_available() -> bool:
    return nimbusware_use_llm_enabled()


def embed_text(
    text: str,
    *,
    mode: EmbeddingMode,
    ollama_base_url: str | None = None,
    ollama_model: str | None = None,
) -> list[float]:
    if mode == "ollama" and ollama_embedding_available():
        try:
            return ollama_embed(
                text,
                base_url=ollama_base_url,
                model=ollama_model,
            )
        except (httpx.HTTPError, ValueError, TypeError):
            return deterministic_embed(text)
    return deterministic_embed(text)
