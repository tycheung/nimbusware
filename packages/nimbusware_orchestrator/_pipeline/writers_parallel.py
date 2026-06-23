from __future__ import annotations

from nimbusware_env.env_flags import env_str, env_truthy, nimbusware_use_llm_enabled
from nimbusware_orchestrator._pipeline._helpers import (
    UUID,
    Any,
    EventType,
    Path,
    StageFailedEvent,
    StageFailedPayload,
    StagePassedEvent,
    StagePassedPayload,
    StageStartedEvent,
    StageStartedPayload,
    WriterStageResult,
    asyncio,
    datetime,
    run_frontend_writer_stage,
    run_parallel_writer_group,
    run_test_writer_stage,
    time,
    timezone,
    uuid4,
)
from nimbusware_orchestrator._pipeline.protocol_hosts import WritersHost


class WritersParallelMixin:
    def _run_writers_parallel_dispatch(
        self: WritersHost,
        run_id: UUID,
        sg_snapshot: dict[str, Any],
        writers_group: list[str],
        *,
        workspace: Path | None = None,
        real_test_writer_enabled: bool = False,
        test_writer_llm_body: bool = False,
        test_writer_llm_stub_fallback_enabled: bool = False,
        test_writer_llm_model_id: str | None = None,
        test_writer_llm_base_url: str = "http://localhost:11434",
        test_writer_llm_timeout_seconds: float = 120.0,
    ) -> tuple[int, str]:
        ws = workspace or Path(env_str("NIMBUSWARE_WORKSPACE") or ".").resolve()
        runners: list[tuple[str, Any]] = []
        if "implementation" in writers_group:
            runners.append(
                (
                    "implementation",
                    lambda: self._parallel_run_implementation(run_id, sg_snapshot, ws),
                ),
            )
        if "test_writer" in writers_group:
            runners.append(
                (
                    "test_writer",
                    lambda: self._parallel_run_test_writer(
                        run_id,
                        sg_snapshot,
                        ws,
                        real_enabled=real_test_writer_enabled,
                        llm_body_enabled=test_writer_llm_body,
                        llm_stub_fallback_enabled=test_writer_llm_stub_fallback_enabled,
                        llm_model_id=test_writer_llm_model_id,
                        llm_base_url=test_writer_llm_base_url,
                        llm_timeout_seconds=test_writer_llm_timeout_seconds,
                    ),
                ),
            )
        if "frontend_writer" in writers_group:
            runners.append(
                (
                    "frontend_writer",
                    lambda: self._parallel_run_frontend_writer(run_id, sg_snapshot, ws),
                ),
            )
        if not runners:
            return self._run_writers_sequential(run_id, sg_snapshot, workspace=workspace)
        from nimbusware_orchestrator.mesh_pipeline_hook import (
            mesh_assign_parallel_stages,
            resolve_mesh_context_for_run,
        )

        stage_names = [name for name, _ in runners]
        session_id, workload, node_ids = resolve_mesh_context_for_run(run_id)
        role_claims: dict[str, str] = {}
        node_users: dict[UUID, str] = {}
        node_caps: dict[UUID, dict[str, Any]] | None = None
        opt_weights: dict[str, float] | None = None
        if session_id is not None:
            from nimbusware_orchestrator.role_claims_mesh import mesh_dispatch_context

            role_claims, node_users, node_caps, opt_weights = mesh_dispatch_context(
                self._store,
                run_id,
                session_id,
            )
        assignments = mesh_assign_parallel_stages(
            run_id=run_id,
            stage_names=stage_names,
            session_id=session_id,
            workload_distribution=workload,
            node_ids=node_ids,
            role_claims=role_claims,
            node_users=node_users,
            node_capabilities=node_caps,
            optimizer_weights=opt_weights,
            workspace=ws,
        )
        from nimbusware_compute.mesh_host_sync import (
            absorb_completed_mesh_units,
            remote_stage_names,
            wait_for_mesh_units,
            writer_stage_result_from_mesh,
        )
        from nimbusware_env.env_flags import env_force_on
        from nimbusware_orchestrator.workflow_parallel_writers import (
            max_parallel_writer_stages_from_governor,
        )

        cap = max_parallel_writer_stages_from_governor()
        if (
            not env_force_on("NIMBUSWARE_PARALLEL_WRITERS")
            and cap is not None
            and len(runners) > cap
        ):
            runners = runners[:cap]
            try:
                from nimbusware_hw.audit import maybe_append_resource_pressure_warn
                from nimbusware_hw.cache import get_cached_profile
                from nimbusware_hw.governor import governor_for_profile

                maybe_append_resource_pressure_warn(
                    self._store,
                    run_id=run_id,
                    governor=governor_for_profile(get_cached_profile()),
                    hook="parallel_writers_cap",
                )
            except ImportError:
                pass
        remote = remote_stage_names(assignments)
        local_runners = [(name, fn) for name, fn in runners if name not in remote]
        results: list[WriterStageResult] = []
        if local_runners:
            results.extend(asyncio.run(run_parallel_writer_group(local_runners)))
        if remote:
            wait_for_mesh_units(run_id, sorted(remote))
            absorb_completed_mesh_units(
                self._store,
                run_id,
                sorted(remote),
                host_workspace=ws,
            )
            for stage_name in sorted(remote):
                results.append(writer_stage_result_from_mesh(run_id, stage_name))
        impl = next(
            (r for r in results if r.stage_name == "implementation"),
            WriterStageResult(stage_name="implementation"),
        )
        return int(impl.verifier_exit_code), str(impl.verifier_log)

    def _complete_frontend_writer(
        self: WritersHost,
        run_id: UUID,
        ws: Path,
        fw_meta: dict[str, Any] | None,
        *,
        dispatch_mode: str,
    ) -> tuple[int, str]:
        started = time.perf_counter()
        code, log, body_mode = run_frontend_writer_stage(ws)
        duration_ms = int((time.perf_counter() - started) * 1000)
        meta = dict(fw_meta or {})
        meta["body_mode"] = body_mode
        if code == 0:
            self._store.append(
                StagePassedEvent(
                    event_type=EventType.STAGE_PASSED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    metadata=meta,
                    payload=StagePassedPayload(
                        stage_name="frontend_writer", duration_ms=duration_ms
                    ),
                ),
            )
            return 0, log
        self._store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata={
                    **meta,
                    "exit_code": code,
                    "failure_reason": "frontend_writer_stage_failed",
                },
                payload=StageFailedPayload(
                    stage_name="frontend_writer",
                    reason_code="frontend_writer_stage_failed",
                    message=(log.strip() or "frontend_writer stage failed")[:500],
                ),
            ),
        )
        return code, log

    def _parallel_run_frontend_writer(
        self: WritersHost,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        ws: Path,
    ) -> WriterStageResult:
        fw_meta = self._writer_stage_started_metadata(
            sg_snapshot,
            "frontend_writer",
            dispatch_mode="parallel",
        )
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata=fw_meta or {},
                payload=StageStartedPayload(stage_name="frontend_writer", attempt=1),
            ),
        )
        code, log = self._complete_frontend_writer(run_id, ws, fw_meta, dispatch_mode="parallel")
        return WriterStageResult(
            stage_name="frontend_writer",
            verifier_exit_code=code,
            verifier_log=log,
        )
