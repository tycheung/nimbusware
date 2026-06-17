from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class MeshScheduler:
    """Host-only scheduler until mesh pipeline assignment ships."""

    mode: str = "host_only"
    spread_policy: str = "spread"
    max_remote_units: int = 4
    _session_nodes: dict[UUID, list[UUID]] = field(default_factory=dict)

    def assign(
        self,
        *,
        parallel_group: str,
        stage_names: list[str],
        session_id: UUID | None = None,
        claims: dict[str, str] | None = None,
    ) -> dict[str, UUID | None]:
        _ = parallel_group, session_id, claims
        return {name: None for name in stage_names}

    def register_session_nodes(self, session_id: UUID, node_ids: list[UUID]) -> None:
        self._session_nodes[session_id] = list(node_ids)

    def online_nodes(self, session_id: UUID | None = None) -> list[UUID]:
        if session_id is None:
            out: list[UUID] = []
            for ids in self._session_nodes.values():
                out.extend(ids)
            return out
        return list(self._session_nodes.get(session_id, []))

    def set_mode(self, mode: str) -> None:
        allowed = {"host_only", "manual_claim", "auto_share", "auto_optimize"}
        self.mode = mode if mode in allowed else "host_only"

    def snapshot(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "spread_policy": self.spread_policy,
            "max_remote_units": self.max_remote_units,
            "session_count": len(self._session_nodes),
        }
