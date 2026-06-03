from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import (  # type: ignore[attr-defined]
    UUID,
    emit_live_integration_adapter_writer_stage,
    emit_stub_integration_adapter_writer_stage,
    integration_adapter_writer_stage_would_emit,
    parse_integration_adapter_writer_workflow_block,
    workflow_profile_from_run_created_rows,
)
from hermes_orchestrator._pipeline.protocol_hosts import IntegrationOptionalStagesHost


class IntegrationOptionalStagesMixin:
    def _maybe_emit_integration_adapter_writer_stage(
        self: IntegrationOptionalStagesHost,
        run_id: UUID,
    ) -> None:
        rows = self._store.list_run_events(str(run_id))
        wf = workflow_profile_from_run_created_rows(rows) or ""
        mat = self._config_materializer
        if not integration_adapter_writer_stage_would_emit(
            self._repo_root,
            wf,
            config_materializer=mat,
        ):
            return
        block = parse_integration_adapter_writer_workflow_block(
            self._repo_root,
            wf,
            config_materializer=mat,
        )
        if block.stub_only:
            emit_stub_integration_adapter_writer_stage(
                self._store,
                run_id=run_id,
                block=block,
            )
        else:
            emit_live_integration_adapter_writer_stage(
                self._store,
                run_id=run_id,
                block=block,
                repo_root=self._repo_root,
            )
