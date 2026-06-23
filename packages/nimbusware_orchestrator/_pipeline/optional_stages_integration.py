from __future__ import annotations

from nimbusware_orchestrator._pipeline._helpers import (
    UUID,
    emit_live_integration_adapter_writer_stage,
    emit_stub_integration_adapter_writer_stage,
    integration_adapter_writer_stage_would_emit,
    parse_integration_adapter_writer_workflow_block,
)
from nimbusware_orchestrator._pipeline.protocol_hosts import IntegrationOptionalStagesHost


class IntegrationOptionalStagesMixin:
    def _maybe_emit_integration_adapter_writer_stage(
        self: IntegrationOptionalStagesHost,
        run_id: UUID,
    ) -> None:
        from nimbusware_orchestrator._pipeline._helpers_runtime import optional_rows_and_profile

        _, wf = optional_rows_and_profile(self, run_id)
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
