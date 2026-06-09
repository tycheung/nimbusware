from __future__ import annotations

from nimbusware_orchestrator._pipeline._helpers import (
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
    SelfRefinementPolicy,
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
    emit_stub_self_refinement_critique_panel,
    execute_self_refinement_critique_llm,
    load_self_refinement_policy,
    os,
    parse_probation_automation_workflow_block,
    parse_self_refinement_workflow_block,
    run_probation_automation,
    self_refinement_llm_critique_effective_for_run,
    self_refinement_ungated_loop_effective,
    timezone,
    try_auto_promote_probation_persona,
    uuid4,
    workflow_profile_from_run_created_rows,
)
from nimbusware_orchestrator._pipeline.protocol_hosts import SelfRefinementOptionalStagesHost

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

        mat = self._config_materializer
        if mat is not None and getattr(mat, "use_db", False):
            from nimbusware_extensions.self_refinement import self_refinement_policy_from_mapping

            try:
                pol = self_refinement_policy_from_mapping(
                    mat.get_self_refinement_policy(),
                )
            except KeyError:
                pol = SelfRefinementPolicy(version=1, enabled=False, description="")
        else:
            path = self._repo_root / "configs" / "self_refinement" / "policy.yaml"
            if path.is_file():
                pol = load_self_refinement_policy(path)
            else:
                pol = SelfRefinementPolicy(version=1, enabled=False, description="")

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
        from nimbusware_config.persist import load_persona_shelf
        from nimbusware_orchestrator.read_models import persona_assignment_from_run_created_metadata

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
        if (
            llm_critique_enabled
            and gate_decision == "hold"
            and self_refinement_llm_critique_effective_for_run(
                self._repo_root,
                wf_prof,
                wf_sr,
                config_materializer=self._config_materializer,
            )
        ):
            base = self._base_cfg()
            runtime = base.get("runtime") or {}
            base_url = str(runtime.get("base_url", "http://localhost:11434"))
            model = self._selected_model_for_run(run_id)
            if model:
                llm_result = execute_self_refinement_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    evaluation_status=eval_status,
                    gaps=eval_gaps,
                    description=bounded,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
                if llm_result is not None:
                    orchestration_branch = "rules_with_llm_critique"
                    llm_critique_attempted = True
                    llm_critique_verdict = Verdict(str(llm_result.get("verdict", "FAIL")))
                    gate_raw = str(llm_result.get("gate_decision", "hold")).strip().lower()
                    llm_gate_decision = "proceed" if gate_raw == "proceed" else "hold"
                    summary_raw = llm_result.get("summary")
                    if isinstance(summary_raw, str) and summary_raw.strip():
                        llm_critique_summary = summary_raw.strip()[:500]
                elif os.environ.get(
                    "NIMBUSWARE_SELF_REFINEMENT_CRITIQUE_STUB",
                    "",
                ).strip().lower() in ("1", "true", "yes"):
                    emit_stub_self_refinement_critique_panel(
                        self._store,
                        self._registry,
                        self._critique_router,
                        run_id=run_id,
                    )
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
