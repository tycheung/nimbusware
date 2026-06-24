from __future__ import annotations

from nimbusware_orchestrator._pipeline._helpers import (
    UUID,
    emit_live_integration_adapter_writer_stage,
    emit_stub_integration_adapter_writer_stage,
    optional_stage_yaml_gate,
    parse_integration_adapter_writer_workflow_block,
)
from nimbusware_orchestrator._pipeline.optional_stage_stub_live_emit import (
    emit_stub_or_live_from_gate,
)
from nimbusware_orchestrator._pipeline.protocol_hosts import IntegrationOptionalStagesHost


class IntegrationOptionalStagesMixin:
    def _maybe_emit_integration_adapter_writer_stage(
        self: IntegrationOptionalStagesHost,
        run_id: UUID,
    ) -> None:
        gated = optional_stage_yaml_gate(
            "NIMBUSWARE_INTEGRATION_ADAPTER_WRITER",
            self,
            run_id,
            parse_integration_adapter_writer_workflow_block,
        )
        if gated is None:
            return
        emit_stub_or_live_from_gate(
            gated,
            emit_stub=lambda block: emit_stub_integration_adapter_writer_stage(
                self._store,
                run_id=run_id,
                block=block,
            ),
            emit_live=lambda block: emit_live_integration_adapter_writer_stage(
                self._store,
                run_id=run_id,
                block=block,
                repo_root=self._repo_root,
            ),
        )
