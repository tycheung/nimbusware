from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from orchestrator._pipeline.protocol_hosts_critique import (
    CritiqueGateHost,
    OptionalCritiqueHost,
)
from orchestrator._pipeline.protocol_hosts_optional import (
    AgentEvaluatorOptionalStagesHost,
    IntegrationOptionalStagesHost,
    IntegratorOptionalStagesHost,
    ResearchOptionalStagesHost,
    SelfRefinementOptionalStagesHost,
    StitchOptionalStagesHost,
)
from orchestrator._pipeline.protocol_hosts_verify import LifecycleVerifyHost
from orchestrator.registry import RoleRegistry
from store.protocol import EventStore

__all__ = [
    "AgentEvaluatorOptionalStagesHost",
    "CritiqueGateHost",
    "EscalationHost",
    "IntegratorOptionalStagesHost",
    "IntegrationOptionalStagesHost",
    "LifecyclePlanHost",
    "LifecycleStartHost",
    "LifecycleVerifyHost",
    "MicroSliceHost",
    "OptionalCritiqueHost",
    "PipelineScraperHost",
    "ResearchOptionalStagesHost",
    "RoleExecuteHost",
    "SelfRefinementOptionalStagesHost",
    "StitchOptionalStagesHost",
    "WritersHost",
]


class LifecycleStartHost(Protocol):
    _store: EventStore

    def _base_cfg(self) -> dict[str, Any]: ...


class PipelineScraperHost(Protocol):
    _store: EventStore
    _repo_root: Path
    _config_materializer: Any | None
    _registry: RoleRegistry

    def policy_snapshot_for_run(self, run_id: UUID) -> dict[str, Any]: ...

    def _persist_scraper_response_artifact(
        self,
        run_id: UUID,
        url_index: int,
        content: bytes,
        persist_cap: int,
    ) -> dict[str, Any]: ...

    def _scraper_get_with_retries(
        self,
        run_id: UUID,
        scraper_url: str,
        actor: UUID,
        client: Any,
        cfg: Any,
        max_response_bytes: int | None,
    ) -> tuple[Any, int]: ...

    def _effective_scraper_budget_bytes(
        self,
        run_id: UUID,
        cfg: Any,
    ) -> int | None: ...

    def _scraper_stage_audit_metadata(
        self,
        host: str,
        http_status: int,
        nbytes: int,
        attempts_used: int,
        *,
        content_length_header: int | None = None,
    ) -> dict[str, Any]: ...

    def _parse_content_length_header(self, resp: Any) -> int | None: ...

    def _scraper_body_digest_and_snippet(
        self,
        content: bytes,
        snippet_max_bytes: int,
    ) -> dict[str, Any]: ...


class LifecyclePlanHost(Protocol):
    _store: EventStore
    _registry: RoleRegistry
    _critique_router: Any
    _repo_root: Path

    def _execute_plan_stage_stub(self, run_id: UUID) -> None: ...
    def _maybe_emit_research_stages(self, run_id: UUID) -> None: ...
    def _maybe_emit_stitch_stages(self, run_id: UUID) -> None: ...
    def _base_cfg(self) -> dict[str, Any]: ...
    def _selected_model_for_run(self, run_id: UUID) -> str | None: ...
    def _run_created_metadata(self, run_id: UUID) -> dict[str, Any]: ...


class EscalationHost(Protocol):
    _store: EventStore
    _repo_root: Path
    _config_materializer: Any | None

    def _workflow_suppresses_automatic_escalation(self, run_id: UUID) -> bool: ...


class MicroSliceHost(Protocol):
    _store: EventStore
    _repo_root: Path
    _memory_chunk_store: Any | None

    def _run_created_metadata(self, run_id: UUID) -> dict[str, Any]: ...


class WritersHost(Protocol):
    _store: EventStore

    def _writer_stage_started_metadata(
        self,
        sg_snapshot: dict[str, Any] | None,
        stage_name: str,
        *,
        dispatch_mode: str | None = None,
    ) -> dict[str, Any] | None: ...

    def _run_writers_sequential(
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        *,
        workspace: Path | None = None,
    ) -> tuple[int, str]: ...
    def _parallel_run_implementation(
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        ws: Path,
    ) -> Any: ...
    def _parallel_run_test_writer(
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        ws: Path,
        **kwargs: Any,
    ) -> Any: ...
    def _complete_frontend_writer(
        self,
        run_id: UUID,
        ws: Path,
        fw_meta: dict[str, Any] | None,
        *,
        dispatch_mode: str,
    ) -> tuple[int, str]: ...
    def _parallel_run_frontend_writer(
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        ws: Path,
    ) -> Any: ...


class RoleExecuteHost(
    LifecyclePlanHost,
    LifecycleVerifyHost,
    IntegratorOptionalStagesHost,
    IntegrationOptionalStagesHost,
    AgentEvaluatorOptionalStagesHost,
    ResearchOptionalStagesHost,
    StitchOptionalStagesHost,
    Protocol,
):
    _registry: RoleRegistry

    def execute_role_for_run(
        self,
        run_id: UUID,
        role_id: str,
        *,
        workspace: Path | None = None,
    ) -> dict[str, object]: ...
