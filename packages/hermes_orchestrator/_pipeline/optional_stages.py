"""Integration adapter, agent evaluator, self-refinement, integrator gate."""

from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import *  # noqa: F403


class OptionalStagesMixin:
    def _maybe_emit_integration_adapter_writer_stage(self, run_id: UUID) -> None:
        rows = self._store.list_run_events(str(run_id))
        wf = workflow_profile_from_run_created_rows(rows)
        mat = self._config_materializer
        if not integration_adapter_writer_stage_would_emit(
            self._repo_root,
            wf,
            config_materializer=mat,
        ):
            return
        block = parse_integration_adapter_writer_workflow_block(
            self._repo_root,
            wf,
            config_materializer=mat,
        )
        if block.stub_only:
            emit_stub_integration_adapter_writer_stage(
                self._store,
                run_id=run_id,
                block=block,
            )
        else:
            emit_live_integration_adapter_writer_stage(
                self._store,
                run_id=run_id,
                block=block,
                repo_root=self._repo_root,
            )


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


    def _maybe_continue_ungated_self_refinement_loop(self, run_id: UUID) -> None:
        """Auto-continue ungated Phase D iterations when the last signal requests it (§14 #17)."""
        for _ in range(16):
            rows = self._store.list_run_events(str(run_id))
            if _self_refinement_max_iterations_exceeded(rows):
                break
            if not _last_self_refinement_loop_should_continue(rows):
                break
            self._maybe_emit_self_refinement_stage_marker(run_id)


    def _maybe_emit_self_refinement_stage_marker(self, run_id: UUID) -> None:
        rows = self._store.list_run_events(str(run_id))
        if _self_refinement_max_iterations_exceeded(rows):
            return

        wf_prof = workflow_profile_from_run_created_rows(rows)
        wf_sr = parse_self_refinement_workflow_block(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )

        mat = self._config_materializer
        if mat is not None and getattr(mat, "use_db", False):
            from hermes_extensions.self_refinement import self_refinement_policy_from_mapping

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
        from hermes_orchestrator.read_models import persona_assignment_from_run_created_metadata

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
        eval_status = eval_status_raw if isinstance(eval_status_raw, str) else None
        gate_decision = "proceed" if (eval_status == "ok" or ungated_loop) else "hold"
        loops_remaining = max(0, int(max_iterations) - int(attempt))
        iteration_progress_ratio = min(1.0, float(attempt) / float(max_iterations))
        should_continue = loops_remaining > 0 and (
            gate_decision == "hold" or ungated_loop
        )
        signal = "phase_d_kickoff" if attempt == 1 else "phase_d_iteration"
        orchestration_branch: Literal["rules", "rules_with_llm_critique"] = "rules"
        llm_critique_attempted = False
        llm_critique_verdict: Verdict | None = None
        llm_gate_decision: Literal["proceed", "hold"] | None = None
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
        eval_gaps = (
            [str(g) for g in eval_gaps_raw]
            if isinstance(eval_gaps_raw, list)
            else []
        )
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
                    llm_gate_decision = (
                        "proceed" if gate_raw == "proceed" else "hold"
                    )
                    summary_raw = llm_result.get("summary")
                    if isinstance(summary_raw, str) and summary_raw.strip():
                        llm_critique_summary = summary_raw.strip()[:500]
                elif os.environ.get(
                    "HERMES_SELF_REFINEMENT_CRITIQUE_STUB",
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
        if auto_promote:
            persona_id = (
                _persona_id_from_assignment_slot(
                    pa_for_eval.get("business_area") if pa_for_eval else None,
                )
                or ""
            )
            if _self_refinement_auto_promote_env_disabled():
                sr_meta["auto_promote_probation"] = {
                    "auto_promote_probation_requested": True,
                    "auto_promote_probation_applied": False,
                    "reason": "env_kill_switch",
                }
            elif persona_id:
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
                    gate_decision=gate_decision,  # explicit per-iteration phase D gate outcome
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


    def _emit_bundle_integrator_gate(self, run_id: UUID) -> None:
        env = os.environ.get("HERMES_EMIT_INTEGRATOR_GATE", "").strip().lower()
        if env in ("0", "false", "no"):
            return
        from hermes_extensions.phase2 import ModuleIntegrator

        rows = self._store.list_run_events(str(run_id))
        wf = workflow_profile_from_run_created_rows(rows)
        mat = self._config_materializer
        yaml_on = load_integrator_gate_emit_enabled(
            self._repo_root,
            config_materializer=mat,
        )
        wf_on = integrator_gate_workflow_enabled(
            self._repo_root,
            wf,
            config_materializer=mat,
        )
        if env not in ("1", "true", "yes") and not yaml_on and not wf_on:
            return
        if mat is None or not getattr(mat, "use_db", False):
            path = self._repo_root / "configs" / "integrator" / "thresholds.yaml"
            if not path.is_file():
                return
        eff_min = effective_integrator_min_score_to_pass(
            self._repo_root,
            wf,
            config_materializer=mat,
        )
        mi = ModuleIntegrator(min_score_to_pass=eff_min)
        bundle_id = select_bundle_id_for_workflow(
            self._repo_root,
            wf,
            config_materializer=self._config_materializer,
        )
        bundle_tags = load_bundle_tags_for_bundle_id(
            self._repo_root,
            bundle_id,
            config_materializer=self._config_materializer,
        )
        bundle_title = load_bundle_title_for_bundle_id(
            self._repo_root,
            bundle_id,
            config_materializer=self._config_materializer,
        )
        project_override = parse_integrator_gate_project_tags(
            self._repo_root,
            wf,
            config_materializer=mat,
        )
        if project_override is not None:
            project_tags = project_override
        elif bundle_tags:
            project_tags = list(bundle_tags)
        else:
            project_tags = [bundle_id]
        profile: dict[str, Any]
        if bundle_tags:
            profile = {"tags": project_tags, "bundle_tags": bundle_tags}
        else:
            profile = {"tags": project_tags}
        score = mi.score_fit(bundle_id, profile)
        ok = mi.passes_gate(bundle_id, profile)
        pset = {str(t).lower() for t in project_tags if str(t).strip()}
        bset = {str(t).lower() for t in bundle_tags if str(t).strip()}
        matched_tags = sorted(pset & bset) if bundle_tags else []
        ranking = rank_bundle_compatibility_candidates(
            self._repo_root,
            list(project_tags),
            integrator=mi,
            config_materializer=self._config_materializer,
            limit=10,
            bundle_outcome_store=self._bundle_outcome_store,
        )
        selected_bundle_rank: int | None = None
        for idx, row in enumerate(ranking):
            if row.get("bundle_id") == bundle_id:
                selected_bundle_rank = idx
                break
        gate_meta: dict[str, Any] = {
            "integrator_gate": True,
            "bundle_id": bundle_id,
            "bundle_title": bundle_title,
            "integrator_score": score,
            "min_score_to_pass": mi.min_score_to_pass,
            "integrator_project_tags": list(project_tags),
            "integrator_bundle_tags": list(bundle_tags),
            "integrator_matched_tags": matched_tags,
            "bundle_compatibility_ranking": ranking,
            "bundle_compatibility_ranking_count": len(ranking),
        }
        if selected_bundle_rank is not None:
            gate_meta["selected_bundle_rank"] = selected_bundle_rank
        verdict = Verdict.PASS if ok else Verdict.FAIL
        from hermes_extensions.bundle_memory import (
            build_bundle_outcome_from_gate,
            bundle_outcome_metadata,
        )

        outcome = build_bundle_outcome_from_gate(
            run_id=run_id,
            bundle_id=bundle_id,
            workflow_profile=wf,
            project_tags=list(project_tags),
            integrator_score=score,
            verdict=verdict,
        )
        gate_meta["bundle_outcome"] = bundle_outcome_metadata(outcome)
        if ok:
            gate_payload = GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.PASS,
                unanimous_pass_required=False,
            )
        else:
            gate_payload = GateDecisionEmittedPayload(
                stage_name="bundle_compatibility",
                verdict=Verdict.FAIL,
                unanimous_pass_required=False,
                failure_reason_code="integrator_below_threshold",
            )
        self._store.append(
            GateDecisionEmittedEvent(
                event_type=EventType.GATE_DECISION_EMITTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata=gate_meta,
                payload=gate_payload,
            ),
        )
        if self._bundle_outcome_store is not None:
            store_seq = self._store.max_store_seq_for_run(str(run_id))
            persisted = build_bundle_outcome_from_gate(
                run_id=run_id,
                bundle_id=bundle_id,
                workflow_profile=wf,
                project_tags=list(project_tags),
                integrator_score=score,
                verdict=verdict,
                source_store_seq=store_seq,
            )
            self._bundle_outcome_store.append(persisted)


