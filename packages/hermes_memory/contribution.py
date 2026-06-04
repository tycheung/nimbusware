"""Rebuild memory index when a run opts in to index contribution (Phase 4)."""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

from hermes_memory.chunking import run_index_contribution_enabled
from hermes_memory.indexer import RebuildIndexResult, rebuild_memory_index
from hermes_memory.store import MemoryChunkStore


def maybe_rebuild_memory_index_for_run(
    memory_store: MemoryChunkStore | None,
    event_store: Any,
    *,
    run_id: UUID,
    repo_root: Any,
    run_created_metadata: dict[str, Any],
) -> RebuildIndexResult | None:
    """Rebuild repo index and emit ``memory.indexed`` when contribution is enabled."""
    if memory_store is None:
        return None
    if not run_index_contribution_enabled(run_created_metadata):
        return None
    try:
        from nimbusware_hw.governor import governor_from_metadata
        from nimbusware_hw.pressure import sample_pressure

        gov = governor_from_metadata(run_created_metadata)
        from nimbusware_hw.pressure import should_defer_memory_rebuild

        level, _ = sample_pressure(gov)
        if should_defer_memory_rebuild(level):
            return None
    except ImportError:
        pass
    conninfo = os.environ.get("NIMBUSWARE_DATABASE_URL", "").strip() or None
    mem_meta = run_created_metadata.get("memory")
    embedding_mode = "deterministic"
    if isinstance(mem_meta, dict) and mem_meta.get("embedding_mode") in ("deterministic", "ollama"):
        embedding_mode = str(mem_meta["embedding_mode"])
    in_memory_rows = None
    if conninfo is None and hasattr(event_store, "list_all_event_rows"):
        in_memory_rows = event_store.list_all_event_rows()
    return rebuild_memory_index(
        memory_store,
        repo_root=repo_root,
        embedding_mode=embedding_mode,  # type: ignore[arg-type]
        conninfo=conninfo,
        in_memory_event_rows=in_memory_rows,
        audit_store=event_store,
        audit_run_id=run_id,
    )
