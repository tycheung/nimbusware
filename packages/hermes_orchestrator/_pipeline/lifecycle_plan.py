from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import (
    UUID,
    emit_stub_plan_stage,
    execute_plan_stage_llm,
    os,
)


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
        if os.environ.get("HERMES_USE_LLM", "").lower() in ("1", "true", "yes"):
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
        self._maybe_emit_stitch_stages(run_id)
