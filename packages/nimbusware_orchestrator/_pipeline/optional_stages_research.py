from __future__ import annotations

from nimbusware_env.env_flags import env_tri_state
from nimbusware_orchestrator._pipeline._helpers import UUID, parse_research_workflow_block
from nimbusware_orchestrator._pipeline.optional_stage_helpers import (
    optional_meta_section,
    optional_rows_and_profile,
    optional_tri_allows_emit,
)
from nimbusware_orchestrator._pipeline.protocol_hosts import ResearchOptionalStagesHost


class ResearchOptionalStagesMixin:
    def _maybe_emit_research_stages(self: ResearchOptionalStagesHost, run_id: UUID) -> None:
        tri = env_tri_state("NIMBUSWARE_RESEARCH")
        if not optional_tri_allows_emit(tri):
            return
        _rows, wf = optional_rows_and_profile(self, run_id)
        block = parse_research_workflow_block(
            self._repo_root,
            wf,
            config_materializer=self._config_materializer,
        )
        if tri != "on" and not block.enabled:
            return
        research_meta = optional_meta_section(self, run_id, "research")
        meta = self._run_created_metadata(run_id)
        requirements = meta.get("requirements")
        req_dict = requirements if isinstance(requirements, dict) else None
        from nimbusware_research.stages import emit_research_stages_stub

        emit_research_stages_stub(
            self._store,
            self._registry,
            self._critique_router,
            run_id=run_id,
            repo_root=self._repo_root,
            requirements=req_dict,
            research_meta=research_meta,
        )
