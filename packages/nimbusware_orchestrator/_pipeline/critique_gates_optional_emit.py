from __future__ import annotations

from nimbusware_orchestrator._pipeline._helpers import (
    UUID,
    EffectiveUniversalCritique,
    EventType,
    RoleCritiqueEmitSpec,
    StageStartedEvent,
    StageStartedPayload,
    datetime,
    emit_role_critique_optional_for_host,
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
from nimbusware_orchestrator._pipeline.protocol_hosts import CritiqueGateHost


class CritiqueGateOptionalEmitMixin:
    def _emit_test_writer_critique_optional(
        self: CritiqueGateHost,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        emit_role_critique_optional_for_host(
            self,
            run_id,
            eff=eff,
            spec=RoleCritiqueEmitSpec(
                enabled=lambda e: e.tw_enabled,
                llm=lambda e: e.tw_llm,
                stub=lambda e: e.tw_stub,
                execute_llm=execute_test_writer_critique_llm,
                emit_stub=emit_stub_test_writer_critique_panel,
            ),
            verifier_exit_code=verifier_exit_code,
            log_snippet=log_snippet,
        )

    def _emit_planner_critique_optional(
        self: CritiqueGateHost,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        emit_role_critique_optional_for_host(
            self,
            run_id,
            eff=eff,
            spec=RoleCritiqueEmitSpec(
                enabled=lambda e: e.pll_enabled,
                llm=lambda e: e.pll_llm,
                stub=lambda e: e.pll_stub,
                execute_llm=execute_planner_critique_llm,
                emit_stub=emit_stub_planner_critique_panel,
            ),
            verifier_exit_code=verifier_exit_code,
            log_snippet=log_snippet,
        )

    def _emit_frontend_writer_critique_optional(
        self: CritiqueGateHost,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        def _frontend_writer_pre_emit(host: CritiqueGateHost, rid: UUID) -> None:
            sg_snapshot = host._stage_graph_snapshot_for_run(rid)
            if sg_snapshot and "frontend_writer" in stage_graph_node_lookup(sg_snapshot):
                fw_meta = event_metadata_for_stage(sg_snapshot, "frontend_writer")
                if fw_meta:
                    host._store.append(
                        StageStartedEvent(
                            event_type=EventType.STAGE_STARTED,
                            event_id=uuid4(),
                            run_id=rid,
                            occurred_at=datetime.now(timezone.utc),
                            metadata=fw_meta,
                            payload=StageStartedPayload(stage_name="frontend_writer", attempt=1),
                        ),
                    )

        emit_role_critique_optional_for_host(
            self,
            run_id,
            eff=eff,
            spec=RoleCritiqueEmitSpec(
                enabled=lambda e: e.fw_enabled,
                llm=lambda e: e.fw_llm,
                stub=lambda e: e.fw_stub,
                execute_llm=execute_frontend_writer_critique_llm,
                emit_stub=emit_stub_frontend_writer_critique_panel,
                pre_emit=_frontend_writer_pre_emit,
            ),
            verifier_exit_code=verifier_exit_code,
            log_snippet=log_snippet,
        )

    def _emit_module_integrator_critique_optional(
        self: CritiqueGateHost,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        emit_role_critique_optional_for_host(
            self,
            run_id,
            eff=eff,
            spec=RoleCritiqueEmitSpec(
                enabled=lambda e: e.mi_enabled,
                llm=lambda e: e.mi_llm,
                stub=lambda e: e.mi_stub,
                execute_llm=execute_module_integrator_critique_llm,
                emit_stub=emit_stub_module_integrator_critique_panel,
            ),
            verifier_exit_code=verifier_exit_code,
            log_snippet=log_snippet,
        )
