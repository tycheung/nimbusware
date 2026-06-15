from __future__ import annotations

from nimbusware_env.env_flags import env_truthy
from nimbusware_orchestrator._pipeline._helpers import (
    UUID,
    Any,
    Path,
    emit_refactor_stage_and_critique,
    emit_stub_network_resilience_critique_panel,
    emit_stub_performance_critique_panel,
    emit_stub_security_critique_panel,
    execute_network_resilience_critique_llm,
    execute_performance_critique_llm,
    execute_security_critique_llm,
    gate_fail_for_stage,
    network_resilience_critique_effective,
    network_resilience_critique_llm_branch_effective,
    ollama_runtime_from_host,
    parse_network_resilience_critique_workflow_block,
    parse_performance_critique_workflow_block,
    parse_refactor_workflow_block,
    parse_security_critique_workflow_block,
    performance_critique_effective,
    performance_critique_llm_branch_effective,
    refactor_stage_effective,
    run_network_resilience_scan_summary,
    run_security_scan_summary,
    security_critique_effective,
    security_critique_llm_branch_effective,
    stage_graph_node_lookup,
)
from nimbusware_orchestrator._pipeline.protocol_hosts import OptionalCritiqueHost


class OptionalCritiqueMixin:
    def _security_critique_producer_for_run(
        self: OptionalCritiqueHost,
        sg_snapshot: dict[str, Any] | None,
    ) -> str:
        if sg_snapshot and "module_integrator" in stage_graph_node_lookup(sg_snapshot):
            return "module_integrator"
        if sg_snapshot and "frontend_writer" in stage_graph_node_lookup(sg_snapshot):
            return "frontend_writer"
        return "backend_writer"

    def _emit_security_critique_optional(
        self: OptionalCritiqueHost,
        run_id: UUID,
        *,
        workspace: Path | None,
        workflow_profile: str | None,
        sg_snapshot: dict[str, Any] | None,
    ) -> bool:
        from nimbusware_orchestrator._pipeline.scan_critique_emit import (
            ScanCritiqueEmitSpec,
            emit_scan_critique_optional,
        )

        spec = ScanCritiqueEmitSpec(
            parse_block=parse_security_critique_workflow_block,
            effective=security_critique_effective,
            llm_effective=security_critique_llm_branch_effective,
            stage_id="implementation.security_critique",
            run_scan=run_security_scan_summary,
            execute_llm=execute_security_critique_llm,
            emit_stub=emit_stub_security_critique_panel,
        )
        return emit_scan_critique_optional(
            self,
            run_id,
            workspace=workspace,
            workflow_profile=workflow_profile,
            sg_snapshot=sg_snapshot,
            spec=spec,
            gate_fail_for_stage=gate_fail_for_stage,
            ollama_runtime_from_host=ollama_runtime_from_host,
        )

    def _emit_performance_critique_optional(
        self: OptionalCritiqueHost,
        run_id: UUID,
        *,
        workspace: Path | None,
        workflow_profile: str | None,
        sg_snapshot: dict[str, Any] | None,
    ) -> bool:
        from nimbusware_orchestrator._pipeline.scan_critique_emit import (
            ScanCritiqueEmitSpec,
            emit_scan_critique_optional,
        )

        spec = ScanCritiqueEmitSpec(
            parse_block=parse_performance_critique_workflow_block,
            effective=performance_critique_effective,
            llm_effective=performance_critique_llm_branch_effective,
            stage_id="implementation.performance_critique",
            run_scan=run_security_scan_summary,
            execute_llm=execute_performance_critique_llm,
            emit_stub=emit_stub_performance_critique_panel,
        )
        return emit_scan_critique_optional(
            self,
            run_id,
            workspace=workspace,
            workflow_profile=workflow_profile,
            sg_snapshot=sg_snapshot,
            spec=spec,
            gate_fail_for_stage=gate_fail_for_stage,
            ollama_runtime_from_host=ollama_runtime_from_host,
        )

    def _emit_network_resilience_critique_optional(
        self: OptionalCritiqueHost,
        run_id: UUID,
        *,
        workspace: Path | None,
        workflow_profile: str | None,
        sg_snapshot: dict[str, Any] | None,
    ) -> bool:
        from nimbusware_orchestrator._pipeline.scan_critique_emit import (
            ScanCritiqueEmitSpec,
            emit_scan_critique_optional,
            network_resilience_pre_emit,
        )

        spec = ScanCritiqueEmitSpec(
            parse_block=parse_network_resilience_critique_workflow_block,
            effective=network_resilience_critique_effective,
            llm_effective=network_resilience_critique_llm_branch_effective,
            stage_id="implementation.network_resilience_critique",
            run_scan=run_network_resilience_scan_summary,
            execute_llm=execute_network_resilience_critique_llm,
            emit_stub=emit_stub_network_resilience_critique_panel,
            pre_emit=network_resilience_pre_emit,
            with_producer=False,
        )
        return emit_scan_critique_optional(
            self,
            run_id,
            workspace=workspace,
            workflow_profile=workflow_profile,
            sg_snapshot=sg_snapshot,
            spec=spec,
            gate_fail_for_stage=gate_fail_for_stage,
            ollama_runtime_from_host=ollama_runtime_from_host,
        )

    def _emit_refactor_stage_optional(
        self: OptionalCritiqueHost,
        run_id: UUID,
        *,
        workflow_profile: str | None,
    ) -> bool:
        block = parse_refactor_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=self._config_materializer,
        )
        if not refactor_stage_effective(block):
            return False
        eff = self._effective_universal_critique_for_run(run_id)
        force_fail = env_truthy("NIMBUSWARE_REFACTOR_FORCE_FAIL")
        return emit_refactor_stage_and_critique(
            self._store,
            self._registry,
            self._critique_router,
            run_id=run_id,
            block=block,
            unanimous_gate_enforce=eff.unanimous_gate_enforce,
            force_fail=force_fail,
            workspace=Path(self._repo_root),
        )
