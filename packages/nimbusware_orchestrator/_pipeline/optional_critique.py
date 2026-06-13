from __future__ import annotations

from nimbusware_env.env_flags import env_str, env_truthy
from nimbusware_orchestrator._pipeline._helpers import (
    UUID,
    Any,
    EventType,
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
        block = parse_security_critique_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=self._config_materializer,
        )
        if not security_critique_effective(block):
            return False
        ws = workspace or Path(env_str("NIMBUSWARE_WORKSPACE") or ".").resolve()
        scan_summary = run_security_scan_summary(ws)
        producer = self._security_critique_producer_for_run(sg_snapshot)
        eff = self._effective_universal_critique_for_run(run_id)
        enforce = eff.unanimous_gate_enforce
        emitted_llm = False
        if security_critique_llm_branch_effective(block):
            model = self._selected_model_for_run(run_id)
            if model:
                base_url, timeout = ollama_runtime_from_host(self)
                emitted_llm = execute_security_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    producer_tax_key=producer,
                    scan_summary=scan_summary,
                    base_url=base_url,
                    model_id=model,
                    block=block,
                    timeout_seconds=timeout,
                    unanimous_gate_enforce=enforce,
                )
        if not emitted_llm and block.stub:
            emit_stub_security_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
                producer_tax_key=producer,
                scan_summary=scan_summary,
                block=block,
                unanimous_gate_enforce=enforce,
            )
        return gate_fail_for_stage(
            self._store.list_run_events(str(run_id)),
            "implementation.security_critique",
        )

    def _emit_performance_critique_optional(
        self: OptionalCritiqueHost,
        run_id: UUID,
        *,
        workspace: Path | None,
        workflow_profile: str | None,
        sg_snapshot: dict[str, Any] | None,
    ) -> bool:
        block = parse_performance_critique_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=self._config_materializer,
        )
        if not performance_critique_effective(block):
            return False
        ws = workspace or Path(env_str("NIMBUSWARE_WORKSPACE") or ".").resolve()
        scan_summary = run_security_scan_summary(ws)
        producer = self._security_critique_producer_for_run(sg_snapshot)
        eff = self._effective_universal_critique_for_run(run_id)
        enforce = eff.unanimous_gate_enforce
        emitted_llm = False
        if performance_critique_llm_branch_effective(block):
            model = self._selected_model_for_run(run_id)
            if model:
                base_url, timeout = ollama_runtime_from_host(self)
                emitted_llm = execute_performance_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    producer_tax_key=producer,
                    scan_summary=scan_summary,
                    base_url=base_url,
                    model_id=model,
                    block=block,
                    timeout_seconds=timeout,
                    unanimous_gate_enforce=enforce,
                )
        if not emitted_llm and block.stub:
            emit_stub_performance_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
                producer_tax_key=producer,
                scan_summary=scan_summary,
                block=block,
                unanimous_gate_enforce=enforce,
            )
        return gate_fail_for_stage(
            self._store.list_run_events(str(run_id)),
            "implementation.performance_critique",
        )

    def _emit_network_resilience_critique_optional(
        self: OptionalCritiqueHost,
        run_id: UUID,
        *,
        workspace: Path | None,
        workflow_profile: str | None,
        sg_snapshot: dict[str, Any] | None,
    ) -> bool:
        block = parse_network_resilience_critique_workflow_block(
            self._repo_root,
            workflow_profile,
            config_materializer=self._config_materializer,
        )
        if not network_resilience_critique_effective(block):
            return False
        if (
            block.backend_only
            and "backend_writer" not in self._critique_router.known_producer_keys()
        ):
            return False
        ws = workspace or Path(env_str("NIMBUSWARE_WORKSPACE") or ".").resolve()
        scan_summary = run_network_resilience_scan_summary(ws)
        eff = self._effective_universal_critique_for_run(run_id)
        enforce = eff.unanimous_gate_enforce
        emitted_llm = False
        if network_resilience_critique_llm_branch_effective(block):
            model = self._selected_model_for_run(run_id)
            if model:
                base_url, timeout = ollama_runtime_from_host(self)
                emitted_llm = execute_network_resilience_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    scan_summary=scan_summary,
                    base_url=base_url,
                    model_id=model,
                    block=block,
                    timeout_seconds=timeout,
                    unanimous_gate_enforce=enforce,
                )
        if not emitted_llm and block.stub:
            emit_stub_network_resilience_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
                scan_summary=scan_summary,
                block=block,
                unanimous_gate_enforce=enforce,
            )
        return gate_fail_for_stage(
            self._store.list_run_events(str(run_id)),
            "implementation.network_resilience_critique",
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
