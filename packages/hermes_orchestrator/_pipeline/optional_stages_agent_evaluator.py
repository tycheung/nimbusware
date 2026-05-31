"""Optional agent-evaluator stage emission."""

from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import *  # noqa: F403

class AgentEvaluatorOptionalStagesMixin:
    def _maybe_emit_agent_evaluator_stage(self, run_id: UUID) -> None:
        env_raw = os.environ.get("HERMES_AGENT_EVALUATOR", "").strip().lower()
        if env_raw in ("0", "false", "no"):
            return
        env_on = env_raw in ("1", "true", "yes")
        wf = workflow_profile_from_run_created_rows(self._store.list_run_events(str(run_id)))
        block = parse_agent_evaluator_workflow_block(
            self._repo_root,
            wf,
            config_materializer=self._config_materializer,
        )
        if not env_on and not block.enabled:
            return
        ae_meta: dict[str, Any] = {}
        ac_cfg = block.auto_create_persona
        if ac_cfg.enabled:
            if _agent_evaluator_auto_create_env_disabled():
                ae_meta["auto_create_persona"] = {
                    "auto_create_persona_requested": True,
                    "auto_create_persona_applied": False,
                    "reason": "env_kill_switch",
                }
            else:
                ae_meta["auto_create_persona"] = try_auto_create_persona_if_missing(
                    self._repo_root,
                    self._store,
                    persona_id=block.persona_id,
                    run_id=run_id,
                    cfg=ac_cfg,
                    config_materializer=self._config_materializer,
                )
        if block.auto_promote_probation:
            if _agent_evaluator_auto_promote_env_disabled():
                ae_meta["auto_promote_probation"] = {
                    "auto_promote_probation_requested": True,
                    "auto_promote_probation_applied": False,
                    "reason": "env_kill_switch",
                }
            else:
                ae_meta["auto_promote_probation"] = try_auto_promote_probation_persona(
                    self._repo_root,
                    self._store,
                    persona_id=block.persona_id,
                    run_id=run_id,
                    config_materializer=self._config_materializer,
                )
        from nimbusware_config.persist import load_persona_shelf
        from hermes_orchestrator.read_models import persona_assignment_from_run_created_metadata

        rows = self._store.list_run_events(str(run_id))
        pa_for_eval: dict[str, Any] | None = None
        for row in rows:
            if row.get("event_type") != EventType.RUN_CREATED.value:
                continue
            meta_row = row.get("metadata")
            if isinstance(meta_row, dict):
                pa_for_eval = persona_assignment_from_run_created_metadata(meta_row)
            break
        shelf = load_persona_shelf(self._repo_root, materializer=self._config_materializer)
        rules_eval = AgentEvaluator().evaluate(
            block.persona_id,
            persona_assignment=pa_for_eval,
            shelf=shelf,
        )
        ae_meta["evaluation"] = rules_eval
        evaluation_branch: Literal["rules", "rules_with_llm_policy"] = "rules"
        production_scoring_mode = "rules"
        if agent_evaluator_llm_branch_effective(block):
            model = self._selected_model_for_run(run_id)
            llm_result = None
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                llm_result = execute_agent_evaluator_policy_llm(
                    self._store,
                    self._registry,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    rules_eval=rules_eval,
                    persona_id=block.persona_id,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
            if llm_result is None and agent_evaluator_llm_stub_env_enabled():
                llm_result = {
                    "status": str(rules_eval.get("status", "ok")),
                    "gaps": (
                        list(rules_eval.get("gaps"))
                        if isinstance(rules_eval.get("gaps"), list)
                        else []
                    ),
                    "summary": "stub agent-evaluator policy review",
                    "production_scoring_mode": "stub",
                }
            elif llm_result is None and agent_evaluator_production_llm_fallback_enabled(
                block,
            ):
                llm_result = agent_evaluator_rules_derived_llm_evaluation(rules_eval)
            if llm_result is not None:
                evaluation_branch = "rules_with_llm_policy"
                llm_eval_meta: dict[str, Any] = {
                    "status": llm_result.get("status"),
                    "gaps": llm_result.get("gaps"),
                    "summary": llm_result.get("summary"),
                }
                mode_raw = llm_result.get("production_scoring_mode")
                if isinstance(mode_raw, str) and mode_raw.strip():
                    production_scoring_mode = mode_raw.strip()
                else:
                    production_scoring_mode = "llm"
                rules_score = rules_eval.get("score")
                if isinstance(rules_score, (int, float)) and not isinstance(
                    rules_score,
                    bool,
                ):
                    score_f = float(rules_score)
                    llm_eval_meta["policy_score"] = score_f
                    llm_eval_meta["policy_score_band"] = agent_evaluator_score_band(
                        score_f,
                    )
                ae_meta["llm_evaluation"] = llm_eval_meta
        ae_meta["evaluation_branch"] = evaluation_branch
        ae_meta["production_scoring_mode"] = production_scoring_mode
        meta: dict[str, Any] = {}
        if ae_meta:
            meta["agent_evaluator"] = ae_meta
        AgentEvaluator().emit_evaluation_stage_started(
            self._store,
            run_id=run_id,
            persona_id=block.persona_id,
            metadata=meta or None,
        )
        if persona_coverage_critique_effective(block):
            eff = self._effective_universal_critique_for_run(run_id)
            emitted = False
            if persona_coverage_critique_llm_branch_effective(block):
                model = self._selected_model_for_run(run_id)
                if model:
                    base = self._base_cfg()
                    runtime = base.get("runtime") or {}
                    base_url = str(runtime.get("base_url", "http://localhost:11434"))
                    emitted = execute_persona_coverage_critique_llm(
                        self._store,
                        self._registry,
                        self._critique_router,
                        run_id=run_id,
                        rules_eval=rules_eval,
                        base_url=base_url,
                        model_id=model,
                        timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                        unanimous_gate_enforce=eff.unanimous_gate_enforce,
                    )
            if not emitted and block.persona_coverage_critique.stub:
                emit_stub_persona_coverage_critique_panel(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    rules_eval=rules_eval,
                    unanimous_gate_enforce=eff.unanimous_gate_enforce,
                )

