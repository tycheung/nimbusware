from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import (
    UUID,
    emit_stub_plan_stage,
    execute_plan_stage_llm,
)
from nimbusware_env.env_flags import hermes_use_llm_enabled


class LifecyclePlanMixin:
    def _execute_plan_stage_stub(self, run_id: UUID) -> None:
        emit_stub_plan_stage(
            self._store,
            self._registry,
            self._critique_router,
            run_id=run_id,
        )

    def execute_plan_stage(self, run_id: UUID) -> None:
        self._maybe_emit_research_stages(run_id)
        if hermes_use_llm_enabled():
            base = self._base_cfg()
            runtime = base.get("runtime") or {}
            base_url = str(runtime.get("base_url", "http://localhost:11434"))
            model = self._selected_model_for_run(run_id)
            if model:
                try:
                    execute_plan_stage_llm(
                        self._store,
                        self._registry,
                        self._critique_router,
                        run_id=run_id,
                        base_url=base_url,
                        model_id=model,
                        timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                    )
                except Exception:
                    self._execute_plan_stage_stub(run_id)
            else:
                self._execute_plan_stage_stub(run_id)
        else:
            self._execute_plan_stage_stub(run_id)
        meta = self._run_created_metadata(run_id)
        research_meta = meta.get("research")
        if not isinstance(research_meta, dict):
            research_meta = {}
        requirements = meta.get("requirements")
        req_dict = requirements if isinstance(requirements, dict) else None
        from hermes_research.reresearch import maybe_reresearch_after_plan_fail

        if maybe_reresearch_after_plan_fail(
            self._store,
            run_id=run_id,
            repo_root=self._repo_root,
            registry=self._registry,
            critique_router=self._critique_router,
            requirements=req_dict,
            research_meta=research_meta,
        ):
            if hermes_use_llm_enabled():
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                model = self._selected_model_for_run(run_id)
                if model:
                    try:
                        execute_plan_stage_llm(
                            self._store,
                            self._registry,
                            self._critique_router,
                            run_id=run_id,
                            base_url=str(runtime.get("base_url", "http://localhost:11434")),
                            model_id=model,
                            timeout_seconds=float(
                                runtime.get("request_timeout_seconds", 120),
                            ),
                        )
                    except Exception:
                        self._execute_plan_stage_stub(run_id)
                else:
                    self._execute_plan_stage_stub(run_id)
            else:
                self._execute_plan_stage_stub(run_id)
        self._maybe_emit_stitch_stages(run_id)
