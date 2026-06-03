from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import (  # type: ignore[attr-defined]
    UUID,
    parse_research_workflow_block,
    workflow_profile_from_run_created_rows,
)
from hermes_orchestrator._pipeline.protocol_hosts import ResearchOptionalStagesHost
from nimbusware_env.env_flags import env_tri_state


class ResearchOptionalStagesMixin:
    def _maybe_emit_research_stages(self: ResearchOptionalStagesHost, run_id: UUID) -> None:
        tri = env_tri_state("HERMES_RESEARCH")
        if tri == "off":
            return
        rows = self._store.list_run_events(str(run_id))
        wf = workflow_profile_from_run_created_rows(rows) or ""
        block = parse_research_workflow_block(
            self._repo_root,
            wf,
            config_materializer=self._config_materializer,
        )
        if tri != "on" and not block.enabled:
            return
        meta = self._run_created_metadata(run_id)
        research_meta = meta.get("research")
        if not isinstance(research_meta, dict):
            research_meta = {}
        requirements = meta.get("requirements")
        req_dict = requirements if isinstance(requirements, dict) else None
        from hermes_research.stages import emit_research_stages_stub

        emit_research_stages_stub(
            self._store,
            self._registry,
            self._critique_router,
            run_id=run_id,
            repo_root=self._repo_root,
            requirements=req_dict,
            research_meta=research_meta,
        )
