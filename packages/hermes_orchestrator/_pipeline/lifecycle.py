"""Preflight start, plan stage, and writer verifier pass entrypoints."""

from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import *  # noqa: F403


class LifecycleMixin:
    def start_run_after_preflight(self, run_id: UUID) -> None:
        base = self._base_cfg()
        runtime = base.get("runtime") or {}
        models = base.get("models") or {}
        primary = (models.get("primary") or {}).get("id", "llama3.1:8b")
        fb_raw = models.get("fallbacks") or []
        fallbacks = [
            str(x.get("id")) for x in fb_raw if isinstance(x, dict) and x.get("id") is not None
        ]

        base_url = str(runtime.get("base_url", "http://localhost:11434"))
        health = str(runtime.get("health_endpoint", "/api/tags"))
        preflight_cfg = base.get("preflight") if isinstance(base.get("preflight"), dict) else {}

        self._store.append(
            ModelPreflightStartedEvent(
                event_type=EventType.MODEL_PREFLIGHT_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=ModelPreflightStartedPayload(
                    provider=str(runtime.get("provider", "ollama")),
                    base_url=base_url,
                    requested_model_id=primary,
                ),
            ),
        )

        selected, evidence, used_primary = run_model_preflight(
            base_url=base_url,
            health_path=health,
            primary_model_id=primary,
            fallback_model_ids=fallbacks,
            timeout_seconds=float(runtime.get("request_timeout_seconds", 60)),
            preflight_cfg=preflight_cfg,
        )

        checks = list(evidence.get("checks_passed", []))
        self._store.append(
            ModelPreflightPassedEvent(
                event_type=EventType.MODEL_PREFLIGHT_PASSED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=ModelPreflightPassedPayload(
                    provider=str(runtime.get("provider", "ollama")),
                    validated_model_id=selected,
                    context_tokens=int(evidence.get("context_tokens", 8192)),
                    p95_latency_ms=int(evidence.get("p95_latency_ms", 0)),
                    checks_passed=checks,
                    preflight_latency_sample_count=evidence.get("preflight_latency_sample_count"),
                    p95_latency_source=evidence.get("p95_latency_source"),
                    health_latency_samples_ms=_coerce_samples_ms(
                        evidence.get("health_latency_samples_ms"),
                    ),
                ),
            ),
        )
        if used_primary:
            self._store.append(
                ModelSelectedPrimaryEvent(
                    event_type=EventType.MODEL_SELECTED_PRIMARY,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    model_id=selected,
                    payload=ModelSelectedPrimaryPayload(
                        provider=str(runtime.get("provider", "ollama")),
                        model_id=selected,
                    ),
                ),
            )
        else:
            self._store.append(
                ModelSelectedFallbackEvent(
                    event_type=EventType.MODEL_SELECTED_FALLBACK,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    model_id=selected,
                    payload=ModelSelectedFallbackPayload(
                        provider=str(runtime.get("provider", "ollama")),
                        selected_model_id=selected,
                        reason_code="primary_unavailable_or_failed_preflight",
                        original_model_id=primary,
                    ),
                ),
            )
        self._store.append(
            RunStartedEvent(
                event_type=EventType.RUN_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=RunStartedPayload(started_by="orchestrator"),
            ),
        )


    def _execute_plan_stage_stub(self, run_id: UUID) -> None:
        emit_stub_plan_stage(
            self._store,
            self._registry,
            self._critique_router,
            run_id=run_id,
        )


    def execute_plan_stage(self, run_id: UUID) -> None:
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
                    return
                except Exception:
                    pass
        self._execute_plan_stage_stub(run_id)


    def execute_writer_verifier_pass(
        self,
        run_id: UUID,
        *,
        workspace: Path | None = None,
    ) -> None:
        """Append implementation stage + optional pytest finding on failure.

        When ``micro_slice_effective.enabled`` on ``run.created``, runs the per-slice
        chain instead of the default writer/verifier pass.

        After the verifier, optional **implementation.critique** panel: try LLM when
        workflow ``universal_critique.implementation.llm`` or ``HERMES_IMPLEMENTATION_CRITIQUE_LLM``
        (env overrides YAML when non-empty); same for stub critics. Optionally
        **test_writer.critique** / **planner.critique** via workflow ``universal_critique`` or
        the existing ``HERMES_*`` switches.
        Optional **planner.critique** after that via env or workflow
        ``universal_critique.planner`` (same env-over-YAML pattern). Optional ``stage.failed``
        for gate FAIL mirrors implementation / test_writer / planner knobs (env overrides
        workflow when set). Optional **finding.created** (LOW) on last critique gate FAIL
        is off by default; enable via ``emit_finding_on_gate_fail`` or ``HERMES_*``
        env (see ``_maybe_emit_critique_gate_fail_findings``).
        Optional **hard_block_on_gate_fail** (per stage; env
        ``HERMES_*_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL``) skips integrator gate,
        agent-evaluator stage marker, and self-refinement marker when
        that stage's last critique gate is FAIL; anti-deadlock / cumulative escalations still run.
        When **hard_block_on_gate_fail** and the last gate for that stage is FAIL, later
        optional critique panels are **not** run (implementation FAIL skips test_writer and
        planner; test_writer FAIL skips planner only).
        """
        if self._micro_slice_enabled_for_run(run_id):
            self.execute_micro_slice_pass(run_id, workspace=workspace)
            return
        self.run_optional_scraper_fetch_stage(run_id)
        writer = self._registry.resolve("backend_writer")
        sg_snapshot = self._stage_graph_snapshot_for_run(run_id)
        wf_prof = workflow_profile_from_run_created_rows(
            self._store.list_run_events(str(run_id)),
        )
        use_parallel = parallel_writers_enabled(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )
        real_test_writer = test_writer_stage_enabled(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )
        tw_llm_body = test_writer_llm_body_enabled(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )
        tw_llm_stub_fallback = test_writer_llm_stub_fallback(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )
        base_cfg = self._base_cfg()
        runtime_cfg = base_cfg.get("runtime") or {}
        writers_group = (
            parallel_group_members(sg_snapshot, "writers")
            if sg_snapshot and use_parallel
            else []
        )
        if writers_group:
            code, log = self._run_writers_parallel_dispatch(
                run_id,
                sg_snapshot,
                writers_group,
                workspace=workspace,
                real_test_writer_enabled=real_test_writer,
                test_writer_llm_body=tw_llm_body,
                test_writer_llm_stub_fallback_enabled=tw_llm_stub_fallback,
                test_writer_llm_model_id=self._selected_model_for_run(run_id),
                test_writer_llm_base_url=str(runtime_cfg.get("base_url", "http://localhost:11434")),
                test_writer_llm_timeout_seconds=float(
                    runtime_cfg.get("request_timeout_seconds", 120),
                ),
            )
        else:
            code, log = self._run_writers_sequential(
                run_id,
                sg_snapshot,
                workspace=workspace,
            )
        if code != 0:
            ctx = self._strictness_context(run_id)
            hinted = suggest_owner_role_from_verifier_log(log, self._registry)
            owner = hinted or writer
            scan_meta: dict[str, Any] = {}
            if security_scan_metadata_on_verify_enabled(
                self._repo_root,
                wf_prof,
                config_materializer=self._config_materializer,
            ):
                ws = workspace or Path(os.environ.get("HERMES_WORKSPACE", ".")).resolve()
                scode, slog, ruff_ec, bandit_ec, mypy_ec, perf_ec, n1_ec, semgrep_ec = (
                    run_security_scan(ws)
                )
                scan_meta = {
                    "security_scan_exit": scode,
                    "security_scan_ruff_exit": ruff_ec,
                    "security_scan_bandit_exit": bandit_ec,
                    "security_scan_mypy_exit": mypy_ec,
                    "security_scan_ruff_perf_exit": perf_ec,
                    "security_scan_n_plus_one_exit": n1_ec,
                    "security_scan_snippet": "\n".join(slog.splitlines()[:20]),
                    **security_scan_tool_summary(
                        ruff_ec,
                        bandit_ec,
                        mypy_ec,
                        perf_ec,
                        n1_ec,
                        semgrep_ec,
                    ),
                }
            payload = FindingCreatedPayload.model_validate(
                {
                    "finding_id": str(uuid4()),
                    "category": "verify",
                    "owner_role": str(owner),
                    "severity": Severity.LOW.value,
                    "source_artifact": "writer_verifier_bundle",
                    "repro_steps": log.splitlines()[:40],
                    "required_fixes": [],
                },
                context=ctx,
            )
            self._store.append(
                FindingCreatedEvent(
                    event_type=EventType.FINDING_CREATED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    metadata=scan_meta,
                    payload=payload,
                ),
            )
            self._maybe_escalate_verifier_failure_checkpoint(run_id)

        log_snippet = "\n".join(log.splitlines()[:60])
        eff = self._effective_universal_critique_for_run(run_id)
        security_gate_fail = self._emit_security_critique_optional(
            run_id,
            workspace=workspace,
            workflow_profile=wf_prof,
            sg_snapshot=sg_snapshot,
        )
        performance_gate_fail = False
        if not security_gate_fail:
            performance_gate_fail = self._emit_performance_critique_optional(
                run_id,
                workspace=workspace,
                workflow_profile=wf_prof,
                sg_snapshot=sg_snapshot,
            )
        network_gate_fail = False
        if not security_gate_fail and not performance_gate_fail:
            network_gate_fail = self._emit_network_resilience_critique_optional(
                run_id,
                workspace=workspace,
                workflow_profile=wf_prof,
                sg_snapshot=sg_snapshot,
            )
        refactor_gate_fail = False
        if not security_gate_fail and not performance_gate_fail and not network_gate_fail:
            refactor_gate_fail = self._emit_refactor_stage_optional(
                run_id,
                workflow_profile=wf_prof,
            )
        impl_llm = eff.impl_llm
        stub_impl = eff.impl_stub
        emitted_impl_llm = False
        if impl_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_impl_llm = execute_implementation_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if (
            not security_gate_fail
            and not performance_gate_fail
            and not network_gate_fail
            and not refactor_gate_fail
            and not emitted_impl_llm
            and stub_impl
        ):
            emit_stub_implementation_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )
        self._maybe_emit_stage_failed_for_implementation_critique_gate_fail(run_id, eff)
        if security_gate_fail or performance_gate_fail or network_gate_fail or refactor_gate_fail:
            return
        rows_post_impl = self._store.list_run_events(str(run_id))
        if not self._critique_impl_hard_block_gate_fail(rows_post_impl, eff):
            self._emit_test_writer_critique_optional(
                run_id,
                verifier_exit_code=code,
                log_snippet=log_snippet,
                eff=eff,
            )
            self._maybe_emit_stage_failed_for_test_writer_critique_gate_fail(run_id, eff)
            rows_post_tw = self._store.list_run_events(str(run_id))
            if not self._critique_tw_hard_block_gate_fail(rows_post_tw, eff):
                self._emit_planner_critique_optional(
                    run_id,
                    verifier_exit_code=code,
                    log_snippet=log_snippet,
                    eff=eff,
                )
                self._maybe_emit_stage_failed_for_planner_critique_gate_fail(run_id, eff)
                rows_post_pll = self._store.list_run_events(str(run_id))
                if not self._critique_pll_hard_block_gate_fail(rows_post_pll, eff):
                    self._emit_frontend_writer_critique_optional(
                        run_id,
                        verifier_exit_code=code,
                        log_snippet=log_snippet,
                        eff=eff,
                    )
                    self._maybe_emit_stage_failed_for_frontend_writer_critique_gate_fail(
                        run_id,
                        eff,
                    )
                    rows_post_fw = self._store.list_run_events(str(run_id))
                    if not self._critique_fw_hard_block_gate_fail(rows_post_fw, eff):
                        self._emit_module_integrator_critique_optional(
                            run_id,
                            verifier_exit_code=code,
                            log_snippet=log_snippet,
                            eff=eff,
                        )
                        self._maybe_emit_stage_failed_for_module_integrator_critique_gate_fail(
                            run_id,
                            eff,
                        )
        self._maybe_emit_critique_gate_fail_findings(run_id, eff)
        self._maybe_auto_escalate(run_id)
        self._maybe_notice_escalate_findings(run_id)
        skip_critique_downstream = self._should_skip_critique_downstream_tail(run_id, eff)
        if not skip_critique_downstream:
            self._emit_bundle_integrator_gate(run_id)
            self._maybe_emit_integration_adapter_writer_stage(run_id)
            self._maybe_emit_agent_evaluator_stage(run_id)
        self._maybe_emit_anti_deadlock_escalation(run_id)
        self._maybe_escalate_after_cumulative_stage_failures(run_id)
        self._maybe_escalate_after_cumulative_gate_failures(run_id)
        self._maybe_escalate_after_cumulative_high_severity_findings(run_id)
        if not skip_critique_downstream:
            self._maybe_emit_self_refinement_stage_marker(run_id)
            self._maybe_continue_ungated_self_refinement_loop(run_id)


    def dispatch_or_run_verify(
        self,
        run_id: UUID,
        *,
        workspace: Path | None = None,
    ) -> str:
        """Enqueue verify when dispatch enabled; otherwise run synchronously."""
        if not run_dispatch_enabled():
            self.execute_writer_verifier_pass(run_id, workspace=workspace)
            return "sync"
        payload: dict[str, Any] = {}
        if workspace is not None:
            payload["workspace"] = str(workspace)
        get_run_queue().enqueue(
            RunDispatchTask(run_id=str(run_id), step="verify", payload=payload),
        )
        return "queued"


    def process_verify_dispatch_task(self, task: RunDispatchTask) -> None:
        ws_raw = task_payload_workspace(task.payload)
        ws = Path(ws_raw) if ws_raw else None
        self.execute_writer_verifier_pass(UUID(task.run_id), workspace=ws)

