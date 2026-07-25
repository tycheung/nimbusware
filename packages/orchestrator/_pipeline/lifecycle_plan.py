from __future__ import annotations

from env.env_flags import nimbusware_use_llm_enabled
from orchestrator._pipeline._helpers import (
    UUID,
    emit_stub_plan_stage,
    execute_plan_stage_llm,
    optional_meta_section,
)
from orchestrator._pipeline.protocol_hosts import LifecyclePlanHost
from orchestrator.llm.peel_guard import _llm_broker_miss_or_transport  # sak499-e

_PLAN_BROKER_MISS = (
    "broker_miss: lifecycle_plan: plan LLM unavailable under NIMBUSWARE_BROKER_LLM=1|2"
)


class LifecyclePlanMixin:
    def _execute_plan_stage_stub(self: LifecyclePlanHost, run_id: UUID) -> None:
        emit_stub_plan_stage(
            self._store,
            self._registry,
            self._critique_router,
            run_id=run_id,
        )

    def execute_plan_stage(self: LifecyclePlanHost, run_id: UUID) -> None:
        self._maybe_emit_research_stages(run_id)
        if nimbusware_use_llm_enabled():
            base = self._base_cfg()
            runtime = base.get("runtime") or {}
            base_url = str(runtime.get("base_url", "http://localhost:11434"))
            model = self._selected_model_for_run(run_id)
            if model:
                try:
                    execute_plan_stage_llm(  # sak497-b: chat_facade peel_strict
                        self._store,
                        self._registry,
                        self._critique_router,
                        run_id=run_id,
                        base_url=base_url,
                        model_id=model,
                        timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                    )
                except RuntimeError as exc:
                    from broker_client.flags import broker_llm_enabled

                    if broker_llm_enabled():  # sak496-a / sak498-i
                        raise
                    if _llm_broker_miss_or_transport(exc):
                        self._execute_plan_stage_stub(run_id)
                    else:
                        raise
            else:
                from broker_client.flags import broker_llm_enabled

                if broker_llm_enabled():  # sak496-a
                    raise RuntimeError(_PLAN_BROKER_MISS)
                self._execute_plan_stage_stub(run_id)
        else:
            self._execute_plan_stage_stub(run_id)
        meta = self._run_created_metadata(run_id)
        research_meta = optional_meta_section(self, run_id, "research")
        requirements = meta.get("requirements")
        req_dict = requirements if isinstance(requirements, dict) else None
        from research.reresearch import maybe_reresearch_after_plan_fail

        if maybe_reresearch_after_plan_fail(
            self._store,
            run_id=run_id,
            repo_root=self._repo_root,
            registry=self._registry,
            critique_router=self._critique_router,
            requirements=req_dict,
            research_meta=research_meta,
        ):
            if nimbusware_use_llm_enabled():
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                model = self._selected_model_for_run(run_id)
                if model:
                    try:
                        execute_plan_stage_llm(  # sak497-b: chat_facade peel_strict
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
                    except RuntimeError as exc:
                        from broker_client.flags import broker_llm_enabled

                        if broker_llm_enabled():  # sak496-a / sak498-i
                            raise
                        if _llm_broker_miss_or_transport(exc):
                            self._execute_plan_stage_stub(run_id)
                        else:
                            raise
                else:
                    from broker_client.flags import broker_llm_enabled

                    if broker_llm_enabled():  # sak496-a
                        raise RuntimeError(_PLAN_BROKER_MISS)
                    self._execute_plan_stage_stub(run_id)
            else:
                self._execute_plan_stage_stub(run_id)
        self._maybe_emit_stitch_stages(run_id)
