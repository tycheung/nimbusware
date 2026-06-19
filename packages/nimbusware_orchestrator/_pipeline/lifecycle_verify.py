from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from nimbusware_env.env_flags import env_str
from nimbusware_orchestrator._pipeline._helpers import (
    UUID,
    Any,
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    Path,
    RunDispatchTask,
    Severity,
    datetime,
    emit_stub_implementation_critique_panel,
    execute_implementation_critique_llm,
    get_run_queue,
    parallel_critics_enabled,
    parallel_group_members,
    parallel_writers_enabled,
    refactor_post_stitch_gate_failed,
    run_dispatch_enabled,
    run_security_scan,
    security_scan_metadata_on_verify_enabled,
    security_scan_tool_summary,
    suggest_owner_role_from_verifier_log,
    task_payload_workspace,
    test_writer_llm_body_enabled,
    test_writer_llm_stub_fallback,
    test_writer_stage_enabled,
    timezone,
    uuid4,
    workflow_profile_from_run_created_rows,
)
from nimbusware_orchestrator._pipeline.protocol_hosts import LifecycleVerifyHost


class LifecycleVerifyMixin:
    def execute_writer_verifier_pass(
        self: LifecycleVerifyHost,
        run_id: UUID,
        *,
        workspace: Path | None = None,
    ) -> None:
        """Implementation writer/verifier pass with optional universal critique panels."""
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
            parallel_group_members(sg_snapshot, "writers") if sg_snapshot and use_parallel else []
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
                ws = workspace or Path(env_str("NIMBUSWARE_WORKSPACE") or ".").resolve()
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
        skip_fast_matrix = self._fast_slice_should_skip_optional_critique_matrix(run_id)
        security_gate_fail = False
        performance_gate_fail = False
        network_gate_fail = False
        refactor_gate_fail = False
        gov_meta: dict[str, Any] | None = None
        for row in self._store.list_run_events(str(run_id)):
            if row.get("event_type") != "run.created":
                continue
            raw = (row.get("metadata") or {}).get("resource_governor")
            gov_meta = raw if isinstance(raw, dict) else None
            break
        if not skip_fast_matrix:
            if parallel_critics_enabled(
                self._repo_root,
                wf_prof,
                resource_governor=gov_meta,
                config_materializer=self._config_materializer,
            ):
                from nimbusware_orchestrator.mesh_pipeline_hook import (
                    mesh_assign_parallel_critics,
                    resolve_mesh_context_for_run,
                )

                mesh_sid, mesh_workload, mesh_nodes = resolve_mesh_context_for_run(run_id)
                assignments = mesh_assign_parallel_critics(
                    run_id=run_id,
                    session_id=mesh_sid,
                    workload_distribution=mesh_workload,
                    node_ids=mesh_nodes,
                    workspace=workspace,
                    workflow_profile=wf_prof,
                )
                from nimbusware_compute.mesh_host_sync import (
                    critic_gate_fail_from_mesh,
                    remote_stage_names,
                )

                remote = remote_stage_names(assignments)

                def _critic_gate(
                    stage_name: str,
                    emit_fn: Any,
                ) -> bool:
                    if stage_name in remote:
                        return critic_gate_fail_from_mesh(run_id, stage_name)
                    return bool(
                        emit_fn(
                            run_id,
                            workspace=workspace,
                            workflow_profile=wf_prof,
                            sg_snapshot=sg_snapshot,
                        ),
                    )

                with ThreadPoolExecutor(max_workers=3) as pool:
                    sec_f = pool.submit(
                        _critic_gate,
                        "security_critique",
                        self._emit_security_critique_optional,
                    )
                    perf_f = pool.submit(
                        _critic_gate,
                        "performance_critique",
                        self._emit_performance_critique_optional,
                    )
                    net_f = pool.submit(
                        _critic_gate,
                        "network_resilience_critique",
                        self._emit_network_resilience_critique_optional,
                    )
                    security_gate_fail = sec_f.result()
                    performance_gate_fail = perf_f.result()
                    network_gate_fail = net_f.result()
            else:
                security_gate_fail = self._emit_security_critique_optional(
                    run_id,
                    workspace=workspace,
                    workflow_profile=wf_prof,
                    sg_snapshot=sg_snapshot,
                )
                if not security_gate_fail:
                    performance_gate_fail = self._emit_performance_critique_optional(
                        run_id,
                        workspace=workspace,
                        workflow_profile=wf_prof,
                        sg_snapshot=sg_snapshot,
                    )
                if not security_gate_fail and not performance_gate_fail:
                    network_gate_fail = self._emit_network_resilience_critique_optional(
                        run_id,
                        workspace=workspace,
                        workflow_profile=wf_prof,
                        sg_snapshot=sg_snapshot,
                    )
            if not security_gate_fail and not performance_gate_fail and not network_gate_fail:
                refactor_gate_fail = self._emit_refactor_stage_optional(
                    run_id,
                    workflow_profile=wf_prof,
                )
        post_stitch_gate_fail = (
            False
            if skip_fast_matrix
            else refactor_post_stitch_gate_failed(self._store.list_run_events(str(run_id)))
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
            and not post_stitch_gate_fail
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
        if (
            security_gate_fail
            or performance_gate_fail
            or network_gate_fail
            or refactor_gate_fail
            or post_stitch_gate_fail
        ):
            return
        rows_post_impl = self._store.list_run_events(str(run_id))
        if not skip_fast_matrix and not self._critique_impl_hard_block_gate_fail(
            rows_post_impl,
            eff,
        ):
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
        skip_critique_downstream = (
            self._should_skip_critique_downstream_tail(
                run_id,
                eff,
            )
            or skip_fast_matrix
        )
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
        self: LifecycleVerifyHost,
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

    def process_verify_dispatch_task(self: LifecycleVerifyHost, task: RunDispatchTask) -> None:
        ws_raw = task_payload_workspace(task.payload)
        ws = Path(ws_raw) if ws_raw else None
        self.execute_writer_verifier_pass(UUID(task.run_id), workspace=ws)
