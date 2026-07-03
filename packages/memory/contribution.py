from __future__ import annotations

from typing import Any
from uuid import UUID

from env.env_flags import nimbusware_database_url
from memory.chunking import run_index_contribution_enabled
from memory.indexer import RebuildIndexResult, rebuild_memory_index
from memory.store import MemoryChunkStore


def maybe_rebuild_memory_index_for_run(
    memory_store: MemoryChunkStore | None,
    event_store: Any,
    *,
    run_id: UUID,
    repo_root: Any,
    run_created_metadata: dict[str, Any],
) -> RebuildIndexResult | None:
    if memory_store is None:
        return None
    if not run_index_contribution_enabled(run_created_metadata):
        return None
    try:
        from hw.governor import governor_from_metadata
        from hw.pressure import sample_pressure

        gov = governor_from_metadata(run_created_metadata)
        from hw.pressure import should_defer_memory_rebuild

        level, details = sample_pressure(gov)
        if should_defer_memory_rebuild(level):
            try:
                from hw.audit import maybe_append_resource_pressure_warn

                maybe_append_resource_pressure_warn(
                    event_store,
                    run_id=run_id,
                    governor=gov,
                    hook="memory_rebuild_defer",
                    level=level,
                    details=details if isinstance(details, dict) else {},
                )
            except ImportError:
                pass
            return None
    except ImportError:
        pass
    conninfo = nimbusware_database_url()
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
