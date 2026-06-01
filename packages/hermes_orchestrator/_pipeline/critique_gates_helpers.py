from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import (
    FRONTEND_WRITER_CRITIQUE_STAGE,
    IMPLEMENTATION_CRITIQUE_STAGE,
    MODULE_INTEGRATOR_CRITIQUE_STAGE,
    PLANNER_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
    UUID,
    Any,
    EffectiveUniversalCritique,
    EventType,
    FindingCreatedEvent,
    FindingCreatedPayload,
    Severity,
    Verdict,
    datetime,
    timezone,
    uuid4,
)


class CritiqueGateHelpersMixin:
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

