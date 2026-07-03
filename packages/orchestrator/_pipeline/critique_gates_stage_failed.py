from __future__ import annotations

from orchestrator._pipeline._helpers import (
    FRONTEND_WRITER_CRITIQUE_STAGE,
    IMPLEMENTATION_CRITIQUE_STAGE,
    MODULE_INTEGRATOR_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
    UUID,
    Any,
    EffectiveUniversalCritique,
    EventType,
    StageFailedEvent,
    StageFailedPayload,
    Verdict,
    datetime,
    timezone,
    uuid4,
)
from orchestrator._pipeline.protocol_hosts import CritiqueGateHost


class CritiqueGateStageFailedMixin:
    def _maybe_emit_stage_failed_for_implementation_critique_gate_fail(
        self: CritiqueGateHost,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
        u = eff if eff is not None else self._effective_universal_critique_for_run(run_id)
        if not u.impl_stage_failed_on_gate_fail:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "implementation_critique_gate_fail"
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
        self: CritiqueGateHost,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
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
        self: CritiqueGateHost,
        run_id: UUID,
        eff: EffectiveUniversalCritique | None = None,
    ) -> None:
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
        self: CritiqueGateHost,
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
        self: CritiqueGateHost,
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
