from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import (
    UUID,
    EffectiveUniversalCritique,
    EventType,
    StageStartedEvent,
    StageStartedPayload,
    datetime,
    emit_stub_frontend_writer_critique_panel,
    emit_stub_module_integrator_critique_panel,
    emit_stub_planner_critique_panel,
    emit_stub_test_writer_critique_panel,
    event_metadata_for_stage,
    execute_frontend_writer_critique_llm,
    execute_module_integrator_critique_llm,
    execute_planner_critique_llm,
    execute_test_writer_critique_llm,
    stage_graph_node_lookup,
    timezone,
    uuid4,
)
from hermes_orchestrator._pipeline.protocol_hosts import CritiqueGateHost


class CritiqueGateOptionalEmitMixin:
    def _emit_test_writer_critique_optional(
        self: CritiqueGateHost,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        """Optional **test_writer.critique** after implementation critique (§14 #16).

        Master switch ``HERMES_ENABLE_TEST_WRITER_CRITIQUE`` or workflow
        ``universal_critique.test_writer.enabled``. LLM / stub envs follow the same
        env-over-YAML pattern.
        """
        if not eff.tw_enabled:
            return
        tw_llm = eff.tw_llm
        stub_tw = eff.tw_stub
        emitted_tw_llm = False
        if tw_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_tw_llm = execute_test_writer_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=verifier_exit_code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if not emitted_tw_llm and stub_tw:
            emit_stub_test_writer_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )

    def _emit_planner_critique_optional(
        self: CritiqueGateHost,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        """Optional **planner.critique** after **test_writer.critique** (§14 #16).

        Master switch ``HERMES_ENABLE_PLANNER_CRITIQUE`` or workflow
        ``universal_critique.planner.enabled``.
        """
        if not eff.pll_enabled:
            return
        pll_llm = eff.pll_llm
        stub_pll = eff.pll_stub
        emitted_pll_llm = False
        if pll_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_pll_llm = execute_planner_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=verifier_exit_code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if not emitted_pll_llm and stub_pll:
            emit_stub_planner_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )

    def _emit_frontend_writer_critique_optional(
        self: CritiqueGateHost,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        if not eff.fw_enabled:
            return
        sg_snapshot = self._stage_graph_snapshot_for_run(run_id)
        if sg_snapshot and "frontend_writer" in stage_graph_node_lookup(sg_snapshot):
            fw_meta = event_metadata_for_stage(sg_snapshot, "frontend_writer")
            if fw_meta:
                self._store.append(
                    StageStartedEvent(
                        event_type=EventType.STAGE_STARTED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        metadata=fw_meta,
                        payload=StageStartedPayload(stage_name="frontend_writer", attempt=1),
                    ),
                )
        emitted_fw_llm = False
        if eff.fw_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_fw_llm = execute_frontend_writer_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=verifier_exit_code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if not emitted_fw_llm and eff.fw_stub:
            emit_stub_frontend_writer_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )

    def _emit_module_integrator_critique_optional(
        self: CritiqueGateHost,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        if not eff.mi_enabled:
            return
        emitted_mi_llm = False
        if eff.mi_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_mi_llm = execute_module_integrator_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=verifier_exit_code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if not emitted_mi_llm and eff.mi_stub:
            emit_stub_module_integrator_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )
