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
    event_metadata_for_stage,
    os,
    run_frontend_writer_stage,
    run_parallel_writer_group,
    run_test_writer_stage,
    run_writer_verifier_bundle,
    stage_graph_node_lookup,
    time,
    timezone,
    uuid4,
)
from nimbusware_orchestrator._pipeline.protocol_hosts import WritersHost


from nimbusware_orchestrator._pipeline.writers_parallel import WritersParallelMixin


class WritersMixin(WritersParallelMixin):
    def _writer_stage_started_metadata(
        self,
        sg_snapshot: dict[str, Any] | None,
        stage_name: str,
        *,
        dispatch_mode: str | None = None,
    ) -> dict[str, Any] | None:
        meta = dict(event_metadata_for_stage(sg_snapshot, stage_name))
        if dispatch_mode:
            meta["dispatch_mode"] = dispatch_mode
        return meta or None

    def _run_writers_sequential(
        self: WritersHost,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        *,
        workspace: Path | None = None,
    ) -> tuple[int, str]:
        ws = workspace or Path(env_str("NIMBUSWARE_WORKSPACE") or ".").resolve()
        impl_meta = self._writer_stage_started_metadata(
            sg_snapshot,
            "implementation",
            dispatch_mode="sequential",
        )
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata=impl_meta or {},
                payload=StageStartedPayload(stage_name="implementation", attempt=1),
            ),
        )
        if sg_snapshot and "test_writer" in stage_graph_node_lookup(sg_snapshot):
            tw_meta = self._writer_stage_started_metadata(
                sg_snapshot,
                "test_writer",
                dispatch_mode="sequential",
            )
            if tw_meta:
                self._store.append(
                    StageStartedEvent(
                        event_type=EventType.STAGE_STARTED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        metadata=tw_meta or {},
                        payload=StageStartedPayload(stage_name="test_writer", attempt=1),
                    ),
                )
        if sg_snapshot and "frontend_writer" in stage_graph_node_lookup(sg_snapshot):
            fw_meta = self._writer_stage_started_metadata(
                sg_snapshot,
                "frontend_writer",
                dispatch_mode="sequential",
            )
            if fw_meta:
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
                code, log = self._complete_frontend_writer(
                    run_id, ws, fw_meta, dispatch_mode="sequential"
                )
                if code != 0:
                    return code, log
        from nimbusware_orchestrator.verify_fanout import (
            run_writer_verifier_resolved as _verify_bundle,
        )

        return _verify_bundle(ws, run_id=str(run_id))

    def _parallel_run_implementation(
        self: WritersHost,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        ws: Path,
    ) -> WriterStageResult:
        started = time.perf_counter()
        impl_meta = self._writer_stage_started_metadata(
            sg_snapshot,
            "implementation",
            dispatch_mode="parallel",
        )
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata=impl_meta or {},
                payload=StageStartedPayload(stage_name="implementation", attempt=1),
            ),
        )
        from nimbusware_orchestrator.verify_fanout import (
            run_writer_verifier_resolved as _verify_bundle,
        )

        code, log = _verify_bundle(ws, run_id=str(run_id))
        duration_ms = int((time.perf_counter() - started) * 1000)
        self._store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StagePassedPayload(
                    stage_name="implementation",
                    duration_ms=duration_ms,
                ),
            ),
        )
        return WriterStageResult(
            stage_name="implementation",
            verifier_exit_code=code,
            verifier_log=log,
        )

    def _parallel_run_test_writer(
        self: WritersHost,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        ws: Path,
        *,
        real_enabled: bool,
        llm_body_enabled: bool,
        llm_stub_fallback_enabled: bool,
        llm_model_id: str | None,
        llm_base_url: str,
        llm_timeout_seconds: float,
    ) -> WriterStageResult:
        delay_raw = env_str("NIMBUSWARE_PARALLEL_WRITER_TEST_DELAY_SECONDS")
        if delay_raw:
            try:
                time.sleep(float(delay_raw))
            except ValueError:
                pass
        started = time.perf_counter()
        tw_meta = (
            self._writer_stage_started_metadata(
                sg_snapshot,
                "test_writer",
                dispatch_mode="parallel",
            )
            or {}
        )
        body_mode = "subprocess"
        if llm_body_enabled and nimbusware_use_llm_enabled():
            body_mode = "llm"
            if env_truthy("NIMBUSWARE_TEST_WRITER_LLM_STUB"):
                body_mode = "stub"
        tw_meta["body_mode"] = body_mode
        self._store.append(
            StageStartedEvent(
                event_type=EventType.STAGE_STARTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata=tw_meta,
                payload=StageStartedPayload(stage_name="test_writer", attempt=1),
            ),
        )
        code = 0
        log = ""
        if real_enabled:
            code, log, body_mode = run_test_writer_stage(
                ws,
                llm_body_enabled=llm_body_enabled,
                llm_stub_fallback=llm_stub_fallback_enabled,
                llm_model_id=llm_model_id,
                llm_base_url=llm_base_url,
                llm_timeout_seconds=llm_timeout_seconds,
            )
        duration_ms = int((time.perf_counter() - started) * 1000)
        if code == 0:
            self._store.append(
                StagePassedEvent(
                    event_type=EventType.STAGE_PASSED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    metadata={"exit_code": 0, "body_mode": body_mode},
                    payload=StagePassedPayload(stage_name="test_writer", duration_ms=duration_ms),
                ),
            )
        else:
            self._store.append(
                StageFailedEvent(
                    event_type=EventType.STAGE_FAILED,
                    event_id=uuid4(),
                    run_id=run_id,
                    occurred_at=datetime.now(timezone.utc),
                    metadata={
                        "exit_code": code,
                        "body_mode": body_mode,
                        "failure_reason": "test_writer_stage_failed",
                    },
                    payload=StageFailedPayload(
                        stage_name="test_writer",
                        reason_code="test_writer_stage_failed",
                        message=(log.strip() or "test_writer stage failed")[:500],
                    ),
                ),
            )
        return WriterStageResult(
            stage_name="test_writer",
            verifier_exit_code=code,
            verifier_log=log,
        )

