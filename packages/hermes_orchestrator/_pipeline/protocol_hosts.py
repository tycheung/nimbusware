"""Protocol host types for strict-checked pipeline mixins."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from hermes_orchestrator.registry import RoleRegistry
from hermes_orchestrator.slice_gate import SliceGateChainResult
from hermes_store.protocol import EventStore


class LifecycleStartHost(Protocol):
    _store: EventStore

    def _base_cfg(self) -> dict[str, Any]: ...


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
    def _parallel_run_frontend_writer_stub(
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
    ) -> Any: ...


class LifecycleVerifyHost(Protocol):
    _store: EventStore
    _registry: RoleRegistry
    _repo_root: Path
    _config_materializer: Any | None
    _critique_router: Any

    def _micro_slice_enabled_for_run(self, run_id: UUID) -> bool: ...
    def execute_micro_slice_pass(
        self,
        run_id: UUID,
        *,
        workspace: Path | None = None,
    ) -> list[Any]: ...
    def run_optional_scraper_fetch_stage(self, run_id: UUID) -> None: ...
    def execute_writer_verifier_pass(
        self,
        run_id: UUID,
        *,
        workspace: Path | None = None,
    ) -> None: ...
    def _stage_graph_snapshot_for_run(self, run_id: UUID) -> dict[str, Any] | None: ...
    def _base_cfg(self) -> dict[str, Any]: ...
    def _run_writers_parallel_dispatch(
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        writers_group: list[str],
        *,
        workspace: Path | None = None,
        **kwargs: Any,
    ) -> tuple[int, str]: ...
    def _run_writers_sequential(
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        *,
        workspace: Path | None = None,
    ) -> tuple[int, str]: ...
    def _selected_model_for_run(self, run_id: UUID) -> str | None: ...
    def _strictness_context(self, run_id: UUID) -> Any: ...
    def _maybe_escalate_verifier_failure_checkpoint(self, run_id: UUID) -> None: ...
    def _effective_universal_critique_for_run(self, run_id: UUID) -> Any: ...
    def _emit_security_critique_optional(
        self,
        run_id: UUID,
        *args: Any,
        **kwargs: Any,
    ) -> bool: ...
    def _emit_performance_critique_optional(
        self,
        run_id: UUID,
        *args: Any,
        **kwargs: Any,
    ) -> bool: ...
    def _emit_network_resilience_critique_optional(
        self,
        run_id: UUID,
        *args: Any,
        **kwargs: Any,
    ) -> bool: ...
    def _emit_refactor_stage_optional(
        self,
        run_id: UUID,
        *args: Any,
        **kwargs: Any,
    ) -> bool: ...
    def _maybe_emit_stage_failed_for_implementation_critique_gate_fail(
        self,
        run_id: UUID,
        eff: Any,
    ) -> None: ...
    def _emit_test_writer_critique_optional(
        self,
        run_id: UUID,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
    def _maybe_emit_stage_failed_for_test_writer_critique_gate_fail(
        self,
        run_id: UUID,
        eff: Any,
    ) -> None: ...
    def _critique_impl_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: Any,
    ) -> bool: ...
    def _emit_planner_critique_optional(
        self,
        run_id: UUID,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
    def _maybe_emit_stage_failed_for_planner_critique_gate_fail(
        self,
        run_id: UUID,
        eff: Any,
    ) -> None: ...
    def _critique_tw_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: Any,
    ) -> bool: ...
    def _emit_frontend_writer_critique_optional(
        self,
        run_id: UUID,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
    def _maybe_emit_stage_failed_for_frontend_writer_critique_gate_fail(
        self,
        run_id: UUID,
        eff: Any,
    ) -> None: ...
    def _critique_pll_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: Any,
    ) -> bool: ...
    def _emit_module_integrator_critique_optional(
        self,
        run_id: UUID,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
    def _maybe_emit_stage_failed_for_module_integrator_critique_gate_fail(
        self,
        run_id: UUID,
        eff: Any,
    ) -> None: ...
    def _critique_fw_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: Any,
    ) -> bool: ...
    def _maybe_emit_critique_gate_fail_findings(self, run_id: UUID, eff: Any) -> None: ...
    def _maybe_auto_escalate(self, run_id: UUID) -> None: ...
    def _maybe_notice_escalate_findings(self, run_id: UUID) -> None: ...
    def _should_skip_critique_downstream_tail(self, run_id: UUID, eff: Any) -> bool: ...
    def _emit_bundle_integrator_gate(self, run_id: UUID) -> None: ...
    def _maybe_emit_integration_adapter_writer_stage(self, run_id: UUID) -> None: ...
    def _maybe_emit_agent_evaluator_stage(self, run_id: UUID) -> None: ...
    def _maybe_emit_anti_deadlock_escalation(self, run_id: UUID) -> None: ...
    def _maybe_escalate_after_cumulative_stage_failures(self, run_id: UUID) -> None: ...
    def _maybe_escalate_after_cumulative_gate_failures(self, run_id: UUID) -> None: ...
    def _maybe_escalate_after_cumulative_high_severity_findings(self, run_id: UUID) -> None: ...
    def _maybe_emit_self_refinement_stage_marker(self, run_id: UUID) -> None: ...
    def _maybe_continue_ungated_self_refinement_loop(self, run_id: UUID) -> None: ...
