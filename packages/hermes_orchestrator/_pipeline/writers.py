from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import (
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
    run_parallel_writer_group,
    run_test_writer_stage,
    run_writer_verifier_bundle,
    stage_graph_node_lookup,
    time,
    timezone,
    uuid4,
)


class WritersMixin:
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
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
        *,
        workspace: Path | None = None,
    ) -> tuple[int, str]:
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
                metadata=impl_meta,
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
                        metadata=tw_meta,
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
                        metadata=fw_meta,
                        payload=StageStartedPayload(stage_name="frontend_writer", attempt=1),
                    ),
                )
                self._store.append(
                    StagePassedEvent(
                        event_type=EventType.STAGE_PASSED,
                        event_id=uuid4(),
                        run_id=run_id,
                        occurred_at=datetime.now(timezone.utc),
                        payload=StagePassedPayload(stage_name="frontend_writer", duration_ms=0),
                    ),
                )
        ws = workspace or Path(os.environ.get("HERMES_WORKSPACE", ".")).resolve()
        return run_writer_verifier_bundle(ws)

    def _parallel_run_implementation(
        self,
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
                metadata=impl_meta,
                payload=StageStartedPayload(stage_name="implementation", attempt=1),
            ),
        )
        code, log = run_writer_verifier_bundle(ws)
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
        self,
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
        delay_raw = os.environ.get("HERMES_PARALLEL_WRITER_TEST_DELAY_SECONDS", "").strip()
        if delay_raw:
            try:
                time.sleep(float(delay_raw))
            except ValueError:
                pass
        started = time.perf_counter()
        tw_meta = self._writer_stage_started_metadata(
            sg_snapshot,
            "test_writer",
            dispatch_mode="parallel",
        )
        body_mode = "subprocess"
        if llm_body_enabled and os.environ.get("HERMES_USE_LLM", "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            body_mode = "llm"
            if os.environ.get("HERMES_TEST_WRITER_LLM_STUB", "").strip().lower() in (
                "1",
                "true",
                "yes",
            ):
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

    def _run_writers_parallel_dispatch(
        self,
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
        ws = workspace or Path(os.environ.get("HERMES_WORKSPACE", ".")).resolve()
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
                    lambda: self._parallel_run_frontend_writer_stub(run_id, sg_snapshot),
                ),
            )
        if not runners:
            return self._run_writers_sequential(run_id, sg_snapshot, workspace=workspace)
        results = asyncio.run(run_parallel_writer_group(runners))
        impl = next(
            (r for r in results if r.stage_name == "implementation"),
            WriterStageResult(stage_name="implementation"),
        )
        return impl.verifier_exit_code, impl.verifier_log

    def _parallel_run_frontend_writer_stub(
        self,
        run_id: UUID,
        sg_snapshot: dict[str, Any] | None,
    ) -> WriterStageResult:
        started = time.perf_counter()
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
                metadata=fw_meta,
                payload=StageStartedPayload(stage_name="frontend_writer", attempt=1),
            ),
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        self._store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StagePassedPayload(stage_name="frontend_writer", duration_ms=duration_ms),
            ),
        )
        return WriterStageResult(stage_name="frontend_writer")
