from __future__ import annotations

from nimbusware_env.env_flags import env_tri_state
from nimbusware_orchestrator._pipeline._helpers import (
    UUID,
    emit_refactor_post_stitch_stage_and_critique,
    mapping_or_empty,
    optional_meta_section,
    optional_rows_and_profile,
    optional_tri_allows_emit,
    parse_stitch_workflow_block,
)
from nimbusware_orchestrator._pipeline.protocol_hosts import StitchOptionalStagesHost


class StitchOptionalStagesMixin:
    def _maybe_emit_stitch_stages(self: StitchOptionalStagesHost, run_id: UUID) -> None:
        tri = env_tri_state("NIMBUSWARE_STITCH")
        if not optional_tri_allows_emit(tri):
            return
        rows, wf = optional_rows_and_profile(self, run_id)
        block = parse_stitch_workflow_block(
            self._repo_root,
            wf,
            config_materializer=self._config_materializer,
        )
        if tri != "on" and not block.enabled:
            return
        meta = self._run_created_metadata(run_id)
        stitch_meta = optional_meta_section(self, run_id, "stitch")
        from nimbusware_research.stages_stitch import emit_stitch_stages_stub

        applied = emit_stitch_stages_stub(
            self._store,
            self._registry,
            self._critique_router,
            run_id=run_id,
            repo_root=self._repo_root,
            run_created_metadata=meta,
            stitch_meta=stitch_meta,
            prior_events=rows,
        )
        if not applied:
            return
        if not bool(stitch_meta.get("require_refactor_pass", True)):
            return
        uc = mapping_or_empty(meta.get("universal_critique_effective"))
        unanimous = bool(uc.get("unanimous_gate_enforce"))
        emit_refactor_post_stitch_stage_and_critique(
            self._store,
            self._registry,
            self._critique_router,
            run_id=run_id,
            unanimous_gate_enforce=unanimous,
        )
