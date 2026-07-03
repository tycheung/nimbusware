from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from orchestrator.registry import RoleRegistry
from store.protocol import EventStore


class CritiqueGateHost(Protocol):
    _store: EventStore
    _registry: RoleRegistry
    _critique_router: Any

    def _effective_universal_critique_for_run(self, run_id: UUID) -> Any: ...
    def _strictness_context(self, run_id: UUID) -> Any: ...
    def _selected_model_for_run(self, run_id: UUID) -> str | None: ...
    def _base_cfg(self) -> dict[str, Any]: ...
    def _stage_graph_snapshot_for_run(self, run_id: UUID) -> dict[str, Any] | None: ...

    @staticmethod
    def _critique_gate_verdict_is_fail(gate_payload: dict[str, Any]) -> bool: ...

    @staticmethod
    def _last_critique_gate_payload_for_stage(
        rows: list[dict[str, Any]],
        stage_name: str,
    ) -> dict[str, Any] | None: ...

    @staticmethod
    def _critique_gate_fail_finding_already_emitted(
        rows: list[dict[str, Any]],
        stage_name: str,
    ) -> bool: ...

    def _repro_steps_from_critique_gate(self, gate_pl: dict[str, Any]) -> list[str]: ...

    def _critique_impl_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: Any,
    ) -> bool: ...

    def _critique_tw_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: Any,
    ) -> bool: ...

    def _critique_pll_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: Any,
    ) -> bool: ...

    def _critique_fw_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: Any,
    ) -> bool: ...

    def _critique_mi_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: Any,
    ) -> bool: ...


class OptionalCritiqueHost(Protocol):
    _store: EventStore
    _registry: RoleRegistry
    _critique_router: Any
    _repo_root: Path
    _config_materializer: Any | None

    def _security_critique_producer_for_run(
        self,
        sg_snapshot: dict[str, Any] | None,
    ) -> str: ...
    def _effective_universal_critique_for_run(self, run_id: UUID) -> Any: ...
    def _selected_model_for_run(self, run_id: UUID) -> str | None: ...
    def _base_cfg(self) -> dict[str, Any]: ...
