"""Critique gate failure emitters and hard-block helpers."""

from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import *  # noqa: F403


class CritiqueGatesMixin:
    def _maybe_emit_stage_failed_for_implementation_critique_gate_fail(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
        """Optional: emit ``stage.failed`` when last ``implementation.critique`` gate is FAIL.

        Default off: set ``HERMES_IMPLEMENTATION_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL`` to
        a truthy value so downstream consumers (escalation, timeline) can react without
        changing default CI behavior. When unset, follows workflow ``universal_critique``.
        """
        u = eff if eff is not None else self._effective_universal_critique_for_run(run_id)
        if not u.impl_stage_failed_on_gate_fail:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code")
            == "implementation_critique_gate_fail"
            for r in rows
            if r.get("event_type") == EventType.STAGE_FAILED.value
        ):
            return
        last_impl_gate: dict[str, Any] | None = None
        for r in rows:
            if r.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl = r.get("payload") or {}
            if pl.get("stage_name") != IMPLEMENTATION_CRITIQUE_STAGE:
                continue
            last_impl_gate = pl
        if not last_impl_gate:
            return
        verdict_raw = last_impl_gate.get("verdict")
        is_fail = verdict_raw == Verdict.FAIL or str(verdict_raw).strip().upper() == "FAIL"
        if not is_fail:
            return
        self._store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StageFailedPayload(
                    stage_name=IMPLEMENTATION_CRITIQUE_STAGE,
                    reason_code="implementation_critique_gate_fail",
                    message="implementation.critique gate verdict was FAIL",
                ),
            ),
        )


    def _maybe_emit_stage_failed_for_test_writer_critique_gate_fail(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
        """Optional: emit ``stage.failed`` when last ``test_writer.critique`` gate is FAIL.

        Default off: set ``HERMES_TEST_WRITER_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL`` to a
        truthy value (requires a ``test_writer.critique`` gate event from the optional
        test-writer critique pass). When unset, follows workflow ``universal_critique``.
        """
        u = eff if eff is not None else self._effective_universal_critique_for_run(run_id)
        if not u.tw_stage_failed_on_gate_fail:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "test_writer_critique_gate_fail"
            for r in rows
            if r.get("event_type") == EventType.STAGE_FAILED.value
        ):
            return
        last_tw_gate: dict[str, Any] | None = None
        for r in rows:
            if r.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl = r.get("payload") or {}
            if pl.get("stage_name") != TEST_WRITER_CRITIQUE_STAGE:
                continue
            last_tw_gate = pl
        if not last_tw_gate:
            return
        verdict_raw = last_tw_gate.get("verdict")
        is_fail = verdict_raw == Verdict.FAIL or str(verdict_raw).strip().upper() == "FAIL"
        if not is_fail:
            return
        self._store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StageFailedPayload(
                    stage_name=TEST_WRITER_CRITIQUE_STAGE,
                    reason_code="test_writer_critique_gate_fail",
                    message="test_writer.critique gate verdict was FAIL",
                ),
            ),
        )


    def _maybe_emit_stage_failed_for_planner_critique_gate_fail(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
        """Optional: emit ``stage.failed`` when last ``planner.critique`` gate is FAIL.

        Default off: set ``HERMES_PLANNER_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL`` to a truthy
        value (requires a ``planner.critique`` gate from the optional post-verify panel).
        When unset, follows workflow ``universal_critique``.
        """
        u = eff if eff is not None else self._effective_universal_critique_for_run(run_id)
        if not u.pll_stage_failed_on_gate_fail:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "planner_critique_gate_fail"
            for r in rows
            if r.get("event_type") == EventType.STAGE_FAILED.value
        ):
            return
        last_gate: dict[str, Any] | None = None
        for r in rows:
            if r.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl = r.get("payload") or {}
            if pl.get("stage_name") != PLANNER_CRITIQUE_STAGE:
                continue
            last_gate = pl
        if not last_gate:
            return
        verdict_raw = last_gate.get("verdict")
        is_fail = verdict_raw == Verdict.FAIL or str(verdict_raw).strip().upper() == "FAIL"
        if not is_fail:
            return
        self._store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StageFailedPayload(
                    stage_name=PLANNER_CRITIQUE_STAGE,
                    reason_code="planner_critique_gate_fail",
                    message="planner.critique gate verdict was FAIL",
                ),
            ),
        )


    def _maybe_emit_stage_failed_for_frontend_writer_critique_gate_fail(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
        u = eff if eff is not None else self._effective_universal_critique_for_run(run_id)
        if not u.fw_stage_failed_on_gate_fail:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "frontend_writer_critique_gate_fail"
            for r in rows
            if r.get("event_type") == EventType.STAGE_FAILED.value
        ):
            return
        last_gate = self._last_critique_gate_payload_for_stage(rows, FRONTEND_WRITER_CRITIQUE_STAGE)
        if not last_gate or not self._critique_gate_verdict_is_fail(last_gate):
            return
        self._store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StageFailedPayload(
                    stage_name=FRONTEND_WRITER_CRITIQUE_STAGE,
                    reason_code="frontend_writer_critique_gate_fail",
                    message="frontend_writer.critique gate verdict was FAIL",
                ),
            ),
        )


    def _maybe_emit_stage_failed_for_module_integrator_critique_gate_fail(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
        u = eff if eff is not None else self._effective_universal_critique_for_run(run_id)
        if not u.mi_stage_failed_on_gate_fail:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "module_integrator_critique_gate_fail"
            for r in rows
            if r.get("event_type") == EventType.STAGE_FAILED.value
        ):
            return
        last_gate = self._last_critique_gate_payload_for_stage(
            rows,
            MODULE_INTEGRATOR_CRITIQUE_STAGE,
        )
        if not last_gate or not self._critique_gate_verdict_is_fail(last_gate):
            return
        self._store.append(
            StageFailedEvent(
                event_type=EventType.STAGE_FAILED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                payload=StageFailedPayload(
                    stage_name=MODULE_INTEGRATOR_CRITIQUE_STAGE,
                    reason_code="module_integrator_critique_gate_fail",
                    message="module_integrator.critique gate verdict was FAIL",
                ),
            ),
        )

    @staticmethod

    def _critique_gate_verdict_is_fail(gate_payload: dict[str, Any]) -> bool:
        verdict_raw = gate_payload.get("verdict")
        return verdict_raw == Verdict.FAIL or str(verdict_raw).strip().upper() == "FAIL"

    @staticmethod

    def _last_critique_gate_payload_for_stage(
        rows: list[dict[str, Any]],
        stage_name: str,
    ) -> dict[str, Any] | None:
        last: dict[str, Any] | None = None
        for r in rows:
            if r.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl = r.get("payload") or {}
            if pl.get("stage_name") != stage_name:
                continue
            last = pl
        return last

    @staticmethod

    def _critique_gate_fail_finding_already_emitted(
        rows: list[dict[str, Any]],
        stage_name: str,
    ) -> bool:
        for r in rows:
            if r.get("event_type") != EventType.FINDING_CREATED.value:
                continue
            meta = r.get("metadata") or {}
            if meta.get("critique_gate_fail_finding") and meta.get("stage_name") == stage_name:
                return True
        return False


    def _repro_steps_from_critique_gate(self, gate_pl: dict[str, Any]) -> list[str]:
        lines = [
            f"stage={gate_pl.get('stage_name')}",
            f"verdict={gate_pl.get('verdict')}",
        ]
        code = (gate_pl.get("failure_reason_code") or "").strip()
        if code:
            lines.append(f"failure_reason_code={code}")
        fc = gate_pl.get("failing_critics")
        if isinstance(fc, list) and fc:
            lines.append(f"failing_critics={len(fc)} critic(s)")
        ff = gate_pl.get("failing_finding_ids")
        if isinstance(ff, list) and ff:
            lines.append(f"failing_finding_ids={len(ff)} id(s)")
        return lines[:40]


    def _maybe_emit_critique_gate_fail_findings(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
        """Optional: emit a LOW ``finding.created`` when last critique gate verdict is FAIL.

        Default off: set ``HERMES_*_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL`` (per stage) or
        workflow ``emit_finding_on_gate_fail``. Scoped to **implementation** / **test_writer**
        / **planner** critique stages only.
        """
        u = eff if eff is not None else self._effective_universal_critique_for_run(run_id)
        stages: list[tuple[bool, str, str]] = [
            (u.impl_emit_finding_on_gate_fail, IMPLEMENTATION_CRITIQUE_STAGE, "backend_writer"),
            (u.tw_emit_finding_on_gate_fail, TEST_WRITER_CRITIQUE_STAGE, "test_writer"),
            (u.pll_emit_finding_on_gate_fail, PLANNER_CRITIQUE_STAGE, "planner"),
            (u.fw_emit_finding_on_gate_fail, FRONTEND_WRITER_CRITIQUE_STAGE, "frontend_writer"),
            (
                u.mi_emit_finding_on_gate_fail,
                MODULE_INTEGRATOR_CRITIQUE_STAGE,
                "module_integrator",
            ),
        ]
        rows = self._store.list_run_events(str(run_id))
        ctx = self._strictness_context(run_id)
        for enabled, stage_name, role_key in stages:
            if not enabled:
                continue
            if self._critique_gate_fail_finding_already_emitted(rows, stage_name):
                continue
            gate_pl = self._last_critique_gate_payload_for_stage(rows, stage_name)
            if not gate_pl:
                continue
            if not self._critique_gate_verdict_is_fail(gate_pl):
                continue
            owner = self._registry.resolve(role_key)
            source_artifact = f"critique_gate:{stage_name}"
            finding_id = uuid4()
            payload = FindingCreatedPayload.model_validate(
                {
                    "finding_id": str(finding_id),
                    "category": "critique",
                    "owner_role": str(owner),
                    "severity": Severity.LOW.value,
                    "source_artifact": source_artifact,
                    "repro_steps": self._repro_steps_from_critique_gate(gate_pl),
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
                    metadata={
                        "critique_gate_fail_finding": True,
                        "stage_name": stage_name,
                    },
                    payload=payload,
                ),
            )
            rows = self._store.list_run_events(str(run_id))


    def _critique_impl_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: EffectiveUniversalCritique,
    ) -> bool:
        """True when implementation critique ran and last gate is FAIL with hard-block on."""
        if not (eff.impl_hard_block_on_gate_fail and (eff.impl_llm or eff.impl_stub)):
            return False
        pl = self._last_critique_gate_payload_for_stage(rows, IMPLEMENTATION_CRITIQUE_STAGE)
        return bool(pl and self._critique_gate_verdict_is_fail(pl))


    def _critique_tw_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: EffectiveUniversalCritique,
    ) -> bool:
        """True when test_writer critique ran and last gate is FAIL with hard-block on."""
        if not (
            eff.tw_hard_block_on_gate_fail
            and eff.tw_enabled
            and (eff.tw_llm or eff.tw_stub)
        ):
            return False
        pl = self._last_critique_gate_payload_for_stage(rows, TEST_WRITER_CRITIQUE_STAGE)
        return bool(pl and self._critique_gate_verdict_is_fail(pl))


    def _critique_pll_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: EffectiveUniversalCritique,
    ) -> bool:
        """True when planner critique ran and last gate is FAIL with hard-block on."""
        if not (
            eff.pll_hard_block_on_gate_fail
            and eff.pll_enabled
            and (eff.pll_llm or eff.pll_stub)
        ):
            return False
        pl = self._last_critique_gate_payload_for_stage(rows, PLANNER_CRITIQUE_STAGE)
        return bool(pl and self._critique_gate_verdict_is_fail(pl))


    def _critique_fw_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: EffectiveUniversalCritique,
    ) -> bool:
        if not (eff.fw_hard_block_on_gate_fail and eff.fw_enabled and (eff.fw_llm or eff.fw_stub)):
            return False
        pl = self._last_critique_gate_payload_for_stage(rows, FRONTEND_WRITER_CRITIQUE_STAGE)
        return bool(pl and self._critique_gate_verdict_is_fail(pl))


    def _critique_mi_hard_block_gate_fail(
        self,
        rows: list[dict[str, Any]],
        eff: EffectiveUniversalCritique,
    ) -> bool:
        if not (eff.mi_hard_block_on_gate_fail and eff.mi_enabled and (eff.mi_llm or eff.mi_stub)):
            return False
        pl = self._last_critique_gate_payload_for_stage(rows, MODULE_INTEGRATOR_CRITIQUE_STAGE)
        return bool(pl and self._critique_gate_verdict_is_fail(pl))


    def _should_skip_critique_downstream_tail(
        self,
        run_id: UUID,
        eff: EffectiveUniversalCritique,
    ) -> bool:
        """Skip integrator / agent-evaluator / self-refinement when hard-block + gate FAIL.

        Anti-deadlock and cumulative stage/gate escalations still run afterward (see
        :meth:`execute_writer_verifier_pass` tail ordering).
        """
        rows = self._store.list_run_events(str(run_id))
        return (
            self._critique_impl_hard_block_gate_fail(rows, eff)
            or self._critique_tw_hard_block_gate_fail(rows, eff)
            or self._critique_pll_hard_block_gate_fail(rows, eff)
            or self._critique_fw_hard_block_gate_fail(rows, eff)
            or self._critique_mi_hard_block_gate_fail(rows, eff)
        )


    def _emit_test_writer_critique_optional(
        self,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        """Optional **test_writer.critique** after implementation critique (§14 #16).

        Master switch ``HERMES_ENABLE_TEST_WRITER_CRITIQUE`` or workflow
        ``universal_critique.test_writer.enabled``. LLM / stub envs follow the same
        env-over-YAML pattern.
        """
        if not eff.tw_enabled:
            return
        tw_llm = eff.tw_llm
        stub_tw = eff.tw_stub
        emitted_tw_llm = False
        if tw_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_tw_llm = execute_test_writer_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=verifier_exit_code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if not emitted_tw_llm and stub_tw:
            emit_stub_test_writer_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )


    def _emit_planner_critique_optional(
        self,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        """Optional **planner.critique** after **test_writer.critique** (§14 #16).

        Master switch ``HERMES_ENABLE_PLANNER_CRITIQUE`` or workflow
        ``universal_critique.planner.enabled``.
        """
        if not eff.pll_enabled:
            return
        pll_llm = eff.pll_llm
        stub_pll = eff.pll_stub
        emitted_pll_llm = False
        if pll_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_pll_llm = execute_planner_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=verifier_exit_code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if not emitted_pll_llm and stub_pll:
            emit_stub_planner_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )


    def _emit_frontend_writer_critique_optional(
        self,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        if not eff.fw_enabled:
            return
        sg_snapshot = self._stage_graph_snapshot_for_run(run_id)
        if sg_snapshot and "frontend_writer" in stage_graph_node_lookup(sg_snapshot):
            fw_meta = event_metadata_for_stage(sg_snapshot, "frontend_writer")
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
        emitted_fw_llm = False
        if eff.fw_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_fw_llm = execute_frontend_writer_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=verifier_exit_code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if not emitted_fw_llm and eff.fw_stub:
            emit_stub_frontend_writer_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )


    def _emit_module_integrator_critique_optional(
        self,
        run_id: UUID,
        *,
        verifier_exit_code: int,
        log_snippet: str,
        eff: EffectiveUniversalCritique,
    ) -> None:
        if not eff.mi_enabled:
            return
        emitted_mi_llm = False
        if eff.mi_llm:
            model = self._selected_model_for_run(run_id)
            if model:
                base = self._base_cfg()
                runtime = base.get("runtime") or {}
                base_url = str(runtime.get("base_url", "http://localhost:11434"))
                emitted_mi_llm = execute_module_integrator_critique_llm(
                    self._store,
                    self._registry,
                    self._critique_router,
                    run_id=run_id,
                    base_url=base_url,
                    model_id=model,
                    verifier_exit_code=verifier_exit_code,
                    log_snippet=log_snippet,
                    timeout_seconds=float(runtime.get("request_timeout_seconds", 120)),
                )
        if not emitted_mi_llm and eff.mi_stub:
            emit_stub_module_integrator_critique_panel(
                self._store,
                self._registry,
                self._critique_router,
                run_id=run_id,
            )

