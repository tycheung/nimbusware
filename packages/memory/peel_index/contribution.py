"""Peel stub — local memory contribution under MEMORY peel (sak495-a)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID


def maybe_rebuild_memory_index_for_run(
    memory_chunk_store: Any,
    store: Any,
    *,
    run_id: UUID,
    repo_root: Path,
    run_created_metadata: dict[str, Any] | None = None,
) -> Any | None:
    """Refuse local run index contribution under MEMORY peel (`sak495-a`)."""
    _ = (memory_chunk_store, store, run_id, repo_root, run_created_metadata)
    from broker_client.flags import broker_memory_enabled
    from memory.broker_route import refuse_legacy

    if broker_memory_enabled():
        refuse_legacy(
            "memory index contribution unavailable under NIMBUSWARE_BROKER_MEMORY=1|2; "
            "use SwissArmyNoife memory_index"
        )
    return None


def __getattr__(name: str) -> Callable[..., Any]:
    def _gone(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            f"{__name__}.{name} removed (sak413); use agent_tools.memory_bridge / sak memory_*"
        )

    _gone.__name__ = name
    return _gone
