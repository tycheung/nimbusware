from __future__ import annotations

from orchestrator._pipeline._helpers import (
    UUID,
    EffectiveUniversalCritique,
    EventType,
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
from orchestrator._pipeline.critique_emit_registry import (
    frontend_writer_optional_spec,
    module_integrator_optional_spec,
    planner_optional_spec,
    test_writer_optional_spec,
)
from orchestrator._pipeline.protocol_hosts import CritiqueGateHost


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
            spec=test_writer_optional_spec(),
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
            spec=planner_optional_spec(),
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
            spec=frontend_writer_optional_spec(pre_emit=_frontend_writer_pre_emit),
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
            spec=module_integrator_optional_spec(),
            verifier_exit_code=verifier_exit_code,
            log_snippet=log_snippet,
        )
