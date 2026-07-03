from __future__ import annotations

from orchestrator._pipeline._helpers import (
    UUID,
    optional_meta_section,
    optional_stage_yaml_gate,
    parse_research_workflow_block,
)
from orchestrator._pipeline.protocol_hosts import ResearchOptionalStagesHost


class ResearchOptionalStagesMixin:
    def _maybe_emit_research_stages(self: ResearchOptionalStagesHost, run_id: UUID) -> None:
        gated = optional_stage_yaml_gate(
            "NIMBUSWARE_RESEARCH",
            self,
            run_id,
            parse_research_workflow_block,
        )
        if gated is None:
            return
        _tri, _rows, _wf, block = gated
        research_meta = optional_meta_section(self, run_id, "research")
        meta = self._run_created_metadata(run_id)
        requirements = meta.get("requirements")
        req_dict = requirements if isinstance(requirements, dict) else None
        from research.stages import emit_research_stages_stub

        emit_research_stages_stub(
            self._store,
            self._registry,
            self._critique_router,
            run_id=run_id,
            repo_root=self._repo_root,
            requirements=req_dict,
            research_meta=research_meta,
            live=bool(block.enabled and block.live),
        )
