"""Workflow memory block parsing and slice retrieval (Phase 4 / fo163–fo164)."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from hermes_memory.manifest import default_memory_index_dir, latest_generation_id
from hermes_memory.models import EmbeddingMode, MemoryRetrievalHit
from hermes_memory.repo_scope import repo_scope_hash
from hermes_memory.search import format_memory_excerpt, pinned_generation_id, search_memory
from hermes_memory.store import MemoryChunkStore
from hermes_orchestrator.micro_slice import SlicePlan
from hermes_orchestrator.workflow_profiles import workflow_profile_dict


@dataclass(frozen=True)
class MemoryWorkflowBlock:
    retrieval_enabled: bool = True
    index_contribution: bool = True
    retrieval_k: int = 5
    excerpt_max_chars: int = 2000
    embedding_mode: EmbeddingMode = "deterministic"


def parse_memory_workflow_block(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> MemoryWorkflowBlock:
    wf = workflow_profile_dict(repo_root, workflow_profile, materializer=config_materializer)
    raw = wf.get("memory")
    if not isinstance(raw, dict):
        return MemoryWorkflowBlock()
    return MemoryWorkflowBlock(
        retrieval_enabled=_coerce_bool(raw.get("retrieval_enabled"), default=True),
        index_contribution=_coerce_bool(raw.get("index_contribution"), default=True),
        retrieval_k=max(1, min(20, int(raw.get("retrieval_k", 5) or 5))),
        excerpt_max_chars=max(0, int(raw.get("excerpt_max_chars", 2000) or 2000)),
        embedding_mode=_parse_embedding_mode(raw.get("embedding_mode")),
    )


def memory_effective_metadata(
    block: MemoryWorkflowBlock,
    *,
    run_policy_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build ``run.created`` ``metadata.memory`` from workflow defaults + overrides."""
    mem = {
        "retrieval_enabled": block.retrieval_enabled,
        "index_contribution": block.index_contribution,
        "retrieval_k": block.retrieval_k,
        "excerpt_max_chars": block.excerpt_max_chars,
        "embedding_mode": block.embedding_mode,
    }
    overrides = (run_policy_overrides or {}).get("memory")
    if isinstance(overrides, dict):
        if "retrieval_enabled" in overrides:
            mem["retrieval_enabled"] = _coerce_bool(
                overrides.get("retrieval_enabled"),
                default=bool(mem["retrieval_enabled"]),
            )
        if "index_contribution" in overrides:
            mem["index_contribution"] = _coerce_bool(
                overrides.get("index_contribution"),
                default=bool(mem["index_contribution"]),
            )
        if overrides.get("retrieval_k") is not None:
            mem["retrieval_k"] = max(1, min(20, int(overrides["retrieval_k"])))
        if overrides.get("excerpt_max_chars") is not None:
            mem["excerpt_max_chars"] = max(0, int(overrides["excerpt_max_chars"]))
        if overrides.get("embedding_mode") in ("deterministic", "ollama"):
            mem["embedding_mode"] = str(overrides["embedding_mode"])
    return mem


def resolve_memory_index_version(
    memory_store: MemoryChunkStore | None,
    *,
    repo_root: Path,
) -> str | None:
    """Pinned generation id at run start (manifest or store)."""
    if memory_store is not None:
        gen = pinned_generation_id(memory_store, repo_root=repo_root)
        if gen is not None:
            return str(gen)
    gen_disk = latest_generation_id(default_memory_index_dir(repo_root))
    return str(gen_disk) if gen_disk else None


def run_memory_retrieval_enabled(metadata: object) -> bool:
    """Default True unless ``metadata.memory.retrieval_enabled`` is explicitly false."""
    if not isinstance(metadata, dict):
        return True
    mem = metadata.get("memory")
    if not isinstance(mem, dict):
        return True
    raw = mem.get("retrieval_enabled")
    if raw is None:
        return True
    return _coerce_bool(raw, default=True)


def memory_settings_from_run_metadata(metadata: object) -> MemoryWorkflowBlock:
    if not isinstance(metadata, dict):
        return MemoryWorkflowBlock()
    mem = metadata.get("memory")
    if not isinstance(mem, dict):
        return MemoryWorkflowBlock()
    return MemoryWorkflowBlock(
        retrieval_enabled=_coerce_bool(mem.get("retrieval_enabled"), default=True),
        index_contribution=_coerce_bool(mem.get("index_contribution"), default=True),
        retrieval_k=_env_or_metadata_int("HERMES_MEMORY_RETRIEVAL_K", mem.get("retrieval_k"), default=5, max_val=20),
        excerpt_max_chars=_env_or_metadata_int(
            "HERMES_MEMORY_EXCERPT_MAX_CHARS",
            mem.get("excerpt_max_chars"),
            default=2000,
            max_val=20000,
        ),
        embedding_mode=_parse_embedding_mode(mem.get("embedding_mode")),
    )


def memory_query_from_slice_plan(plan: SlicePlan) -> str:
    parts = [plan.slice_id, plan.rationale, plan.acceptance_criteria]
    parts.extend(plan.target_paths)
    text = " ".join(p for p in parts if p).strip()
    return text or "failure fix gate security"


def memory_query_from_stage_context(stage_context: dict[str, Any] | None) -> str:
    """Build a short retrieval query from slice/stage context."""
    if not stage_context:
        return "failure fix gate security"
    parts: list[str] = []
    for key in ("stage_name", "category", "failure_summary", "task_summary"):
        val = stage_context.get(key)
        if val:
            parts.append(str(val))
    return " ".join(parts) if parts else "failure fix gate security"


def query_digest(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]


def retrieve_memory_excerpt_for_slice(
    memory_store: MemoryChunkStore,
    plan: SlicePlan,
    *,
    repo_root: Path,
    settings: MemoryWorkflowBlock,
) -> tuple[str, list[MemoryRetrievalHit], str]:
    """Search repo memory and return excerpt text, hits, and repo scope hash."""
    query = memory_query_from_slice_plan(plan)
    scope = repo_scope_hash(repo_root)
    hits = search_memory(
        memory_store,
        query,
        repo_root=repo_root,
        k=settings.retrieval_k,
        embedding_mode=settings.embedding_mode,
    )
    excerpt = format_memory_excerpt(hits, max_chars=settings.excerpt_max_chars)
    return excerpt, hits, scope


def pinned_generation_for_scope(
    memory_store: MemoryChunkStore,
    *,
    repo_root: Path,
) -> UUID | None:
    return pinned_generation_id(memory_store, repo_root=repo_root)


def _coerce_bool(raw: object, *, default: bool) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in ("0", "false", "no")


def _parse_embedding_mode(raw: object) -> EmbeddingMode:
    if str(raw or "").strip().lower() == "ollama":
        return "ollama"
    return "deterministic"


def _env_or_metadata_int(
    env_key: str,
    raw: object,
    *,
    default: int,
    max_val: int,
) -> int:
    env_raw = os.environ.get(env_key, "").strip()
    if env_raw:
        try:
            return max(0, min(max_val, int(env_raw)))
        except ValueError:
            pass
    if raw is not None:
        try:
            return max(0, min(max_val, int(raw)))
        except (TypeError, ValueError):
            pass
    return max(0, min(max_val, default))
