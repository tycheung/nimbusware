from __future__ import annotations

from orchestrator._pipeline._helpers import (
    _SELF_REFINEMENT_MAX_ITER_REASON,
    _SELF_REFINEMENT_POLICY_STAGE,
    UUID,
    AgentEvaluator,
    Any,
    EventType,
    Literal,
    SelfRefinementEvaluator,
    SelfRefinementLoopSignalledEvent,
    SelfRefinementLoopSignalledPayload,
    StageFailedEvent,
    StageFailedPayload,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
    _last_self_refinement_loop_should_continue,
    _persona_id_from_assignment_slot,
    _self_refinement_auto_promote_env_disabled,
    _self_refinement_marker_count,
    _self_refinement_max_iterations_exceeded,
    _self_refinement_stage_marker_env_disabled,
    datetime,
    os,
    parse_probation_automation_workflow_block,
    parse_self_refinement_workflow_block,
    run_probation_automation,
    self_refinement_ungated_loop_effective,
    timezone,
    try_auto_promote_probation_persona,
    uuid4,
    workflow_profile_from_run_created_rows,
)
from orchestrator._pipeline.protocol_hosts import SelfRefinementOptionalStagesHost
from orchestrator._pipeline.self_refinement_critique_emit import (
    try_emit_self_refinement_critique_for_host,
)
from orchestrator.workflow.self_refinement_policy import resolve_self_refinement_policy

_SelfRefinementOrchestrationBranch = Literal["rules", "rules_with_llm_critique"]
_LlmGateDecision = Literal["proceed", "hold"]
_SelfRefinementSignal = Literal["phase_d_kickoff", "phase_d_iteration"]
_SelfRefinementEvalStatus = Literal["ok", "invalid", "gap"]


class SelfRefinementOptionalStagesMixin:
    def _maybe_continue_ungated_self_refinement_loop(
        self: SelfRefinementOptionalStagesHost,
        run_id: UUID,
    ) -> None:
        """Auto-continue ungated Phase D iterations when the last signal requests it."""
        for _ in range(16):
            rows = self._store.list_run_events(str(run_id))
            if _self_refinement_max_iterations_exceeded(rows):
                break
            if not _last_self_refinement_loop_should_continue(rows):
                break
            self._maybe_emit_self_refinement_stage_marker(run_id)

    def _maybe_emit_self_refinement_stage_marker(
        self: SelfRefinementOptionalStagesHost,
        run_id: UUID,
    ) -> None:
        rows = self._store.list_run_events(str(run_id))
        if _self_refinement_max_iterations_exceeded(rows):
            return

        wf_prof = workflow_profile_from_run_created_rows(rows) or ""
        wf_sr = parse_self_refinement_workflow_block(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )

        pol = resolve_self_refinement_policy(
            self._repo_root,
            config_materializer=self._config_materializer,
        )

        if not pol.enabled and not wf_sr.enabled:
            return

        if _self_refinement_stage_marker_env_disabled():
            return

        version = pol.version
        description = pol.description
        if wf_sr.version is not None:
            version = wf_sr.version
        if wf_sr.description is not None:
            description = wf_sr.description

        max_iterations = pol.max_iterations
        if wf_sr.max_iterations is not None:
            max_iterations = wf_sr.max_iterations
        auto_promote = bool(pol.auto_promote_probation or wf_sr.auto_promote_probation)
        llm_critique_enabled = bool(
            wf_sr.llm_critique_enabled or pol.llm_critique_enabled,
        )
        ungated_loop = self_refinement_ungated_loop_effective(wf_sr)

        marker_count = _self_refinement_marker_count(rows)
        attempt = marker_count + 1
        if attempt > max_iterations:
            self._store.append(
                StageFailedEvent(
                    event_type=EventType.STAGE_FAILED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    payload=StageFailedPayload(
                        stage_name=_SELF_REFINEMENT_POLICY_STAGE,
                        reason_code=_SELF_REFINEMENT_MAX_ITER_REASON,
                        message=(
                            f"self_refinement:policy exceeded max_iterations={max_iterations}"
                        ),
                    ),
                ),
            )
            return

        bounded = (description or "")[:2000]
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
        sr_eval = SelfRefinementEvaluator().evaluate(
            persona_assignment=pa_for_eval,
            shelf=load_persona_shelf(self._repo_root, materializer=self._config_materializer),
        )
        eval_status_raw = sr_eval.get("status")
        eval_status: _SelfRefinementEvalStatus | None = (
            eval_status_raw if eval_status_raw in ("ok", "invalid", "gap") else None
        )
        gate_decision: _LlmGateDecision = (
            "proceed" if (eval_status == "ok" or ungated_loop) else "hold"
        )
        loops_remaining = max(0, int(max_iterations) - int(attempt))
        iteration_progress_ratio = min(1.0, float(attempt) / float(max_iterations))
        should_continue = loops_remaining > 0 and (gate_decision == "hold" or ungated_loop)
        signal: _SelfRefinementSignal = "phase_d_kickoff" if attempt == 1 else "phase_d_iteration"
        orchestration_branch: _SelfRefinementOrchestrationBranch = "rules"
        llm_critique_attempted = False
        llm_critique_verdict: Verdict | None = None
        llm_gate_decision: _LlmGateDecision | None = None
        llm_critique_summary: str | None = None
        prior_gate_verdict: str | None = None
        for row in rows:
            if row.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl_row = row.get("payload")
            if not isinstance(pl_row, dict):
                continue
            if pl_row.get("stage_name") == "self_refinement.critique":
                verdict_raw = pl_row.get("verdict")
                prior_gate_verdict = (
                    str(verdict_raw).strip().upper() if verdict_raw is not None else None
                )
        eval_gaps_raw = sr_eval.get("gaps")
        eval_gaps = [str(g) for g in eval_gaps_raw] if isinstance(eval_gaps_raw, list) else []
        if eval_status is not None:
            critique_emit = try_emit_self_refinement_critique_for_host(
                self,
                run_id,
                llm_critique_enabled=llm_critique_enabled,
                gate_decision=gate_decision,
                workflow_profile=wf_prof,
                workflow_block=wf_sr,
                evaluation_status=eval_status,
                gaps=eval_gaps,
                description=bounded,
            )
        else:
            critique_emit = {}
        branch_raw = critique_emit.get("orchestration_branch")
        if branch_raw == "rules_with_llm_critique":
            orchestration_branch = "rules_with_llm_critique"
        if critique_emit.get("llm_critique_attempted"):
            llm_critique_attempted = True
        if "llm_critique_verdict" in critique_emit:
            llm_critique_verdict = critique_emit["llm_critique_verdict"]
        gate_emit = critique_emit.get("llm_gate_decision")
        if gate_emit in ("proceed", "hold"):
            llm_gate_decision = gate_emit
        if critique_emit.get("llm_critique_summary"):
            llm_critique_summary = str(critique_emit["llm_critique_summary"])
        sr_meta: dict[str, Any] = {
            "version": version,
            "description": bounded,
            "evaluation": sr_eval,
            "max_iterations": max_iterations,
            "attempt": attempt,
            "signal": signal,
            "gate_decision": gate_decision,
            "loops_remaining": loops_remaining,
            "iteration_progress_ratio": iteration_progress_ratio,
            "should_continue": should_continue,
            "orchestration_branch": orchestration_branch,
            "llm_critique": {
                "enabled": llm_critique_enabled,
                "attempted": llm_critique_attempted,
                "orchestration_branch": orchestration_branch,
                "verdict": (
                    llm_critique_verdict.value if llm_critique_verdict is not None else None
                ),
                "gate_decision": llm_gate_decision,
                "summary": llm_critique_summary,
            },
            "ungated_loop": ungated_loop,
            "ungated_iterative_depth": ungated_loop and attempt > 1,
            "prior_gate_verdict": prior_gate_verdict,
        }
        persona_id = (
            _persona_id_from_assignment_slot(
                pa_for_eval.get("business_area") if pa_for_eval else None,
            )
            or ""
        )
        prob_block = parse_probation_automation_workflow_block(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )
        if prob_block.enabled and persona_id:
            rules_eval = AgentEvaluator().evaluate(
                persona_id,
                persona_assignment=pa_for_eval,
                shelf=load_persona_shelf(self._repo_root, materializer=self._config_materializer),
            )
            sr_meta.update(
                run_probation_automation(
                    self._repo_root,
                    self._store,
                    persona_id=persona_id,
                    run_id=run_id,
                    evaluation=rules_eval,
                    block=prob_block,
                    config_materializer=self._config_materializer,
                    owner_role=str(self._registry.resolve("agent_evaluator")),
                    strictness_context=self._strictness_context(run_id),
                ),
            )
        shelved = bool(
            sr_meta.get("auto_shelve_probation", {}).get("auto_shelve_probation_applied"),
        )
        if auto_promote and not shelved:
            if _self_refinement_auto_promote_env_disabled():
                sr_meta["auto_promote_probation"] = {
                    "auto_promote_probation_requested": True,
                    "auto_promote_probation_applied": False,
                    "reason": "env_kill_switch",
                }
            elif persona_id.strip():
                sr_meta["auto_promote_probation"] = try_auto_promote_probation_persona(
                    self._repo_root,
                    self._store,
                    persona_id=persona_id,
                    run_id=run_id,
                    config_materializer=self._config_materializer,
                    actor="system:self_refinement",
                )
            else:
                sr_meta["auto_promote_probation"] = {
                    "auto_promote_probation_requested": True,
                    "auto_promote_probation_applied": False,
                    "reason": "no_business_area_persona_on_run",
                }
        self._store.append(
            SelfRefinementLoopSignalledEvent(
                event_type=EventType.SELF_REFINEMENT_LOOP_SIGNALLED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=SelfRefinementLoopSignalledPayload(
                    attempt=attempt,
                    max_iterations=max_iterations,
                    signal=signal,
                    gate_decision=gate_decision,
                    evaluation_status=eval_status,
                    loops_remaining=loops_remaining,
                    iteration_progress_ratio=iteration_progress_ratio,
                    should_continue=should_continue,
                    orchestration_branch=orchestration_branch,
                    llm_critique_enabled=llm_critique_enabled,
                    llm_critique_attempted=llm_critique_attempted,
                    llm_critique_verdict=llm_critique_verdict,
                    llm_gate_decision=llm_gate_decision,
                ),
            ),
        )
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata={"self_refinement": sr_meta},
                payload=StageStartedPayload(
                    stage_name=_SELF_REFINEMENT_POLICY_STAGE,
                    attempt=attempt,
                ),
            ),
        )
