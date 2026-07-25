"""Peel stub — local memory capability removed (sak413). Use memory_bridge / sak."""
from __future__ import annotations

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
    from broker_client.flags import broker_memory_enabled
    from memory.broker_route import refuse_legacy

    if broker_memory_enabled():
        refuse_legacy(
            "memory index contribution unavailable under NIMBUSWARE_BROKER_MEMORY=1|2; "
            "use SwissArmyNoife memory_index"
        )
    raise RuntimeError(
        "memory.peel_index.contribution.maybe_rebuild_memory_index_for_run removed (sak413); "
        "use agent_tools.memory_bridge / sak memory_*"
    )


def __getattr__(name: str):
    def _gone(*args, **kwargs):
        raise RuntimeError(
            f"{__name__}.{name} removed (sak413); use agent_tools.memory_bridge / sak memory_*"
        )

    _gone.__name__ = name
    return _gone
