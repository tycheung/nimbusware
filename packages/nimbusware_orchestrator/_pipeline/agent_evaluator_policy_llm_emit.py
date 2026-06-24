from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from nimbusware_orchestrator._pipeline._helpers import (
    agent_evaluator_llm_branch_effective,
    agent_evaluator_llm_stub_env_enabled,
    agent_evaluator_production_llm_fallback_enabled,
    agent_evaluator_rules_derived_llm_evaluation,
    agent_evaluator_score_band,
    execute_agent_evaluator_policy_llm,
)

AgentEvaluatorPolicyBranch = Literal["rules", "rules_with_llm_policy"]


def resolve_agent_evaluator_policy_llm_for_host(
    host: Any,
    run_id: UUID,
    *,
    block: Any,
    rules_eval: dict[str, Any],
) -> tuple[AgentEvaluatorPolicyBranch, str, dict[str, Any] | None]:
    evaluation_branch: AgentEvaluatorPolicyBranch = "rules"
    production_scoring_mode = "rules"
    if not agent_evaluator_llm_branch_effective(block):
        return evaluation_branch, production_scoring_mode, None
    model = host._selected_model_for_run(run_id)
    llm_result = None
    if model:
        base = host._base_cfg()
        runtime = base.get("runtime") or {}
        base_url = str(runtime.get("base_url", "http://localhost:11434"))
        llm_result = execute_agent_evaluator_policy_llm(
            host._store,
            host._registry,
            run_id=run_id,
            base_url=base_url,
            model_id=model,
            rules_eval=rules_eval,
            persona_id=block.persona_id,
            timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
        )
    if llm_result is None and agent_evaluator_llm_stub_env_enabled():
        gaps_raw = rules_eval.get("gaps")
        llm_result = {
            "status": str(rules_eval.get("status", "ok")),
            "gaps": list(gaps_raw) if isinstance(gaps_raw, list) else [],
            "summary": "stub agent-evaluator policy review",
            "production_scoring_mode": "stub",
        }
    elif llm_result is None and agent_evaluator_production_llm_fallback_enabled(block):
        llm_result = agent_evaluator_rules_derived_llm_evaluation(rules_eval)
    if llm_result is None:
        return evaluation_branch, production_scoring_mode, None
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
    if isinstance(rules_score, (int, float)) and not isinstance(rules_score, bool):
        score_f = float(rules_score)
        llm_eval_meta["policy_score"] = score_f
        llm_eval_meta["policy_score_band"] = agent_evaluator_score_band(score_f)
    return evaluation_branch, production_scoring_mode, llm_eval_meta
