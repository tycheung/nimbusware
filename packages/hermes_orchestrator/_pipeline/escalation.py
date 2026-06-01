from __future__ import annotations

from hermes_orchestrator._pipeline._helpers import (
    EventType,
    UUID,
    Verdict,
    append_run_escalated,
    datetime,
    load_anti_deadlock_settings,
    load_auto_escalate_after_cumulative_findings,
    load_escalate_after_cumulative_gate_failures,
    load_escalate_after_cumulative_high_severity_findings,
    load_escalate_after_cumulative_stage_failures,
    load_escalate_on_first_verifier_failure,
    load_notice_escalate_at_cumulative_findings,
    parse_escalation_workflow_block,
    should_emit_anti_deadlock_escalation,
    timezone,
    workflow_profile_from_run_created_rows,
)



class EscalationMixin:
    def _workflow_suppresses_automatic_escalation(self, run_id: UUID) -> bool:
        rows = self._store.list_run_events(str(run_id))
        wf_prof = workflow_profile_from_run_created_rows(rows)
        block = parse_escalation_workflow_block(
            self._repo_root,
            wf_prof,
            config_materializer=self._config_materializer,
        )
        return block.suppress_automatic_escalation


    def _maybe_emit_anti_deadlock_escalation(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        enabled, stall_minutes, min_prog = load_anti_deadlock_settings(self._repo_root)
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "anti_deadlock_insufficient_progress"
            for r in rows
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ):
            return
        if not should_emit_anti_deadlock_escalation(
            rows,
            now=datetime.now(timezone.utc),
            enabled=enabled,
            stall_minutes=stall_minutes,
            min_progress_events=min_prog,
        ):
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="anti_deadlock_insufficient_progress",
            notes=f"stall_minutes={stall_minutes} min_progress_events={min_prog}",
        )


    def _maybe_escalate_after_cumulative_stage_failures(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        threshold = load_escalate_after_cumulative_stage_failures(
            self._repo_root,
            config_materializer=self._config_materializer,
        )
        if threshold is None:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "cumulative_stage_failures"
            for r in rows
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ):
            return
        n_failed = sum(1 for r in rows if r["event_type"] == EventType.STAGE_FAILED.value)
        if n_failed < threshold:
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="cumulative_stage_failures",
            notes=f"threshold={threshold} cumulative_stage_failed={n_failed}",
        )


    def _maybe_escalate_after_cumulative_gate_failures(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        threshold = load_escalate_after_cumulative_gate_failures(
            self._repo_root,
            config_materializer=self._config_materializer,
        )
        if threshold is None:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "cumulative_gate_failures"
            for r in rows
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ):
            return
        n_gate_fail = 0
        for r in rows:
            if r["event_type"] != EventType.GATE_DECISION_EMITTED.value:
                continue
            pl = r.get("payload") or {}
            if pl.get("verdict") == Verdict.FAIL.value:
                n_gate_fail += 1
        if n_gate_fail < threshold:
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="cumulative_gate_failures",
            notes=f"threshold={threshold} cumulative_gate_failed={n_gate_fail}",
        )


    def _maybe_escalate_after_cumulative_high_severity_findings(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        threshold = load_escalate_after_cumulative_high_severity_findings(
            self._repo_root,
            config_materializer=self._config_materializer,
        )
        if threshold is None:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "cumulative_high_severity_findings"
            for r in rows
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ):
            return
        high_n = 0
        for r in rows:
            if r["event_type"] != EventType.FINDING_CREATED.value:
                continue
            sev = (r.get("payload") or {}).get("severity")
            if sev in ("HIGH", "BLOCKER"):
                high_n += 1
        if high_n < threshold:
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="cumulative_high_severity_findings",
            notes=(
                f"threshold={threshold} "
                f"cumulative_high_severity_findings={high_n}"
            ),
        )


    def _maybe_auto_escalate(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        threshold = load_auto_escalate_after_cumulative_findings(
            self._repo_root,
            config_materializer=self._config_materializer,
        )
        if threshold is None:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(r["event_type"] == EventType.RUN_ESCALATED.value for r in rows):
            return
        n_findings = sum(1 for r in rows if r["event_type"] == EventType.FINDING_CREATED.value)
        if n_findings < threshold:
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="cumulative_findings_threshold",
            notes=f"threshold={threshold} cumulative_findings={n_findings}",
        )


    def _maybe_notice_escalate_findings(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        threshold = load_notice_escalate_at_cumulative_findings(
            self._repo_root,
            config_materializer=self._config_materializer,
        )
        if threshold is None:
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "cumulative_findings_notice"
            for r in rows
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ):
            return
        n_findings = sum(1 for r in rows if r["event_type"] == EventType.FINDING_CREATED.value)
        if n_findings < threshold:
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="cumulative_findings_notice",
            notes=f"notice_threshold={threshold} cumulative_findings={n_findings}",
        )


    def _maybe_escalate_verifier_failure_checkpoint(self, run_id: UUID) -> None:
        if self._workflow_suppresses_automatic_escalation(run_id):
            return
        if not load_escalate_on_first_verifier_failure(self._repo_root):
            return
        rows = self._store.list_run_events(str(run_id))
        if any(
            (r.get("payload") or {}).get("reason_code") == "verifier_failure_checkpoint"
            for r in rows
            if r["event_type"] == EventType.RUN_ESCALATED.value
        ):
            return
        append_run_escalated(
            self._store,
            repo_root=self._repo_root,
            run_id=run_id,
            reason_code="verifier_failure_checkpoint",
            notes="escalate_on_first_verifier_failure policy",
        )

