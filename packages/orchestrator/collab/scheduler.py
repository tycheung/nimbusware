from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from orchestrator.collab.optimizer import pick_optimize_node


@dataclass
class MeshScheduler:
    mode: str = "host_only"
    spread_policy: str = "spread"
    max_remote_units: int = 4
    _session_nodes: dict[UUID, list[UUID]] = field(default_factory=dict)
    _session_node_users: dict[UUID, dict[UUID, str]] = field(default_factory=dict)
    _session_node_capabilities: dict[UUID, dict[UUID, dict[str, Any]]] = field(default_factory=dict)
    _session_optimizer_weights: dict[UUID, dict[str, float]] = field(default_factory=dict)

    def assign(
        self,
        *,
        parallel_group: str,
        stage_names: list[str],
        session_id: UUID | None = None,
        claims: dict[str, str] | None = None,
    ) -> dict[str, UUID | None]:
        _ = parallel_group
        claims = claims or {}
        if self.mode == "host_only" or session_id is None:
            return {name: None for name in stage_names}
        nodes = self.online_nodes(session_id)
        if not nodes:
            return {name: None for name in stage_names}
        cap = max(1, self.max_remote_units)
        remote_nodes = nodes[:cap]
        caps = self._session_node_capabilities.get(session_id, {})
        weights = self._session_optimizer_weights.get(session_id, {})
        out: dict[str, UUID | None] = {}
        used: set[UUID] = set()
        idx = 0
        for name in stage_names:
            claimer = claims.get(name) or ""
            if claimer:
                out[name] = self._node_for_claimer(session_id, claimer, nodes)
                continue
            if self.mode == "auto_optimize":
                picked = pick_optimize_node(
                    remote_nodes,
                    node_capabilities=caps,
                    weights=weights,
                    used_nodes=used if self.spread_policy == "spread" else None,
                )
                out[name] = picked
                if picked is not None and self.spread_policy == "spread":
                    used.add(picked)
                continue
            if self.mode in {"manual_claim", "auto_share"}:
                out[name] = remote_nodes[idx % len(remote_nodes)]
                idx += 1
            else:
                out[name] = None
        return out

    def _node_for_claimer(
        self,
        session_id: UUID,
        claimer_user_id: str,
        nodes: list[UUID],
    ) -> UUID | None:
        users = self._session_node_users.get(session_id, {})
        for node_id in nodes:
            if users.get(node_id) == claimer_user_id:
                return node_id
        return None

    def register_session_nodes(
        self,
        session_id: UUID,
        node_ids: list[UUID],
        *,
        node_users: dict[UUID, str] | None = None,
        node_capabilities: dict[UUID, dict[str, Any]] | None = None,
        optimizer_weights: dict[str, float] | None = None,
    ) -> None:
        self._session_nodes[session_id] = list(node_ids)
        if node_users:
            self._session_node_users[session_id] = dict(node_users)
        if node_capabilities:
            self._session_node_capabilities[session_id] = dict(node_capabilities)
        if optimizer_weights:
            self._session_optimizer_weights[session_id] = dict(optimizer_weights)

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


_scheduler = MeshScheduler()


def get_mesh_scheduler() -> MeshScheduler:
    return _scheduler
