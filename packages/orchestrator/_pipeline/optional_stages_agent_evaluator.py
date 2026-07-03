from __future__ import annotations

from env.env_flags import env_tri_state
from orchestrator._pipeline._helpers import (
    UUID,
    AgentEvaluator,
    Any,
    EventType,
    _agent_evaluator_auto_create_env_disabled,
    _agent_evaluator_auto_promote_env_disabled,
    parse_agent_evaluator_workflow_block,
    parse_probation_automation_workflow_block,
    persona_coverage_critique_effective,
    run_probation_automation,
    try_auto_create_persona_if_missing,
    try_auto_promote_probation_persona,
)
from orchestrator._pipeline.agent_evaluator_policy_llm_emit import (
    AgentEvaluatorPolicyBranch,
    resolve_agent_evaluator_policy_llm_for_host,
)
from orchestrator._pipeline.persona_coverage_critique_emit import (
    emit_persona_coverage_critique_optional_for_host,
)
from orchestrator._pipeline.protocol_hosts import AgentEvaluatorOptionalStagesHost

_AgentEvaluatorBranch = AgentEvaluatorPolicyBranch


class AgentEvaluatorOptionalStagesMixin:
    def _maybe_emit_agent_evaluator_stage(
        self: AgentEvaluatorOptionalStagesHost,
        run_id: UUID,
    ) -> None:
        tri = env_tri_state("NIMBUSWARE_AGENT_EVALUATOR")
        if tri == "off":
            return
        from orchestrator._pipeline._helpers_runtime import optional_rows_and_profile

        rows, wf = optional_rows_and_profile(self, run_id)
        block = parse_agent_evaluator_workflow_block(
            self._repo_root,
            wf,
            config_materializer=self._config_materializer,
        )
        if tri != "on" and not block.enabled:
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
        from agent_core.timeline_metadata import persona_assignment_from_run_created_metadata
        from config.persist import load_persona_shelf

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

        prob_block = parse_probation_automation_workflow_block(
            self._repo_root,
            wf,
            config_materializer=self._config_materializer,
        )
        if prob_block.enabled:
            ae_meta.update(
                run_probation_automation(
                    self._repo_root,
                    self._store,
                    persona_id=block.persona_id,
                    run_id=run_id,
                    evaluation=rules_eval,
                    block=prob_block,
                    config_materializer=self._config_materializer,
                    owner_role=str(self._registry.resolve("agent_evaluator")),
                    strictness_context=self._strictness_context(run_id),
                ),
            )
        shelved = bool(
            ae_meta.get("auto_shelve_probation", {}).get("auto_shelve_probation_applied"),
        )
        if block.auto_promote_probation and not shelved:
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

        overlaps = rules_eval.get("scope_overlaps")
        if isinstance(overlaps, list) and overlaps:
            ae_meta["scope_creep_warning"] = "; ".join(
                str(w).strip() for w in overlaps[:3] if str(w).strip()
            )
        evaluation_branch: _AgentEvaluatorBranch = "rules"
        production_scoring_mode = "rules"
        branch, mode, llm_eval_meta = resolve_agent_evaluator_policy_llm_for_host(
            self,
            run_id,
            block=block,
            rules_eval=rules_eval,
        )
        evaluation_branch = branch
        production_scoring_mode = mode
        if llm_eval_meta is not None:
            ae_meta["llm_evaluation"] = llm_eval_meta
        ae_meta["evaluation_branch"] = evaluation_branch
        ae_meta["production_scoring_mode"] = production_scoring_mode
        meta: dict[str, Any] = {}
        if ae_meta:
            meta["agent_evaluator"] = ae_meta
        creep = ae_meta.get("scope_creep_warning")
        if isinstance(creep, str) and creep.strip():
            meta["scope_creep_warning"] = creep.strip()
        AgentEvaluator().emit_evaluation_stage_started(
            self._store,
            run_id=run_id,
            persona_id=block.persona_id,
            metadata=meta or None,
        )
        if persona_coverage_critique_effective(block):
            eff = self._effective_universal_critique_for_run(run_id)
            emit_persona_coverage_critique_optional_for_host(
                self,
                run_id,
                block=block,
                rules_eval=rules_eval,
                unanimous_gate_enforce=eff.unanimous_gate_enforce,
            )
