from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from nimbusware_orchestrator.registry import RoleRegistry
from nimbusware_store.protocol import EventStore


class ResearchOptionalStagesHost(Protocol):
    _store: EventStore
    _registry: RoleRegistry
    _critique_router: Any
    _repo_root: Path
    _config_materializer: Any | None

    def _run_created_metadata(self, run_id: UUID) -> dict[str, Any]: ...


class StitchOptionalStagesHost(Protocol):
    _store: EventStore
    _registry: RoleRegistry
    _critique_router: Any
    _repo_root: Path
    _config_materializer: Any | None

    def _run_created_metadata(self, run_id: UUID) -> dict[str, Any]: ...


class IntegratorOptionalStagesHost(Protocol):
    _store: EventStore
    _repo_root: Path
    _config_materializer: Any | None
    _bundle_outcome_store: Any | None

    def _maybe_emit_integrator_dep_preflight(
        self,
        run_id: UUID,
        *,
        bundle_id: str,
    ) -> None: ...


class IntegrationOptionalStagesHost(Protocol):
    _store: EventStore
    _repo_root: Path
    _config_materializer: Any | None


class SelfRefinementOptionalStagesHost(Protocol):
    _store: EventStore
    _registry: RoleRegistry
    _critique_router: Any
    _repo_root: Path
    _config_materializer: Any | None

    def _selected_model_for_run(self, run_id: UUID) -> str | None: ...
    def _base_cfg(self) -> dict[str, Any]: ...
    def _strictness_context(self, run_id: UUID) -> dict[str, Any]: ...
    def _maybe_emit_self_refinement_stage_marker(self, run_id: UUID) -> None: ...


class AgentEvaluatorOptionalStagesHost(Protocol):
    _store: EventStore
    _registry: RoleRegistry
    _critique_router: Any
    _repo_root: Path
    _config_materializer: Any | None

    def _selected_model_for_run(self, run_id: UUID) -> str | None: ...
    def _base_cfg(self) -> dict[str, Any]: ...
    def _effective_universal_critique_for_run(self, run_id: UUID) -> Any: ...
    def _strictness_context(self, run_id: UUID) -> dict[str, Any]: ...
