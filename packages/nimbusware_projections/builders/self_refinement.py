from __future__ import annotations

from typing import Any

from agent_core.models import EventType
from nimbusware_projections.builders.universal_critique import universal_critique_timeline_entries
from nimbusware_projections.fields.self_refinement import SELF_REFINEMENT_SUMMARY_KEYS

_SELF_REFINEMENT_POLICY_STAGE = "self_refinement:policy"


def self_refinement_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest ``stage.started`` with ``self_refinement:policy`` (self-refinement marker)."""
    out: dict[str, Any] | None = None
    marker_count = 0
    first_marker_occurred_at: Any = None
    last_marker_occurred_at: Any = None
    want = EventType.STAGE_STARTED.value
    max_iterations: Any = None
    for ev in events:
        if ev.get("event_type") != want:
            continue
        payload = ev.get("payload")
        pl: dict[str, Any] = payload if isinstance(payload, dict) else {}
        sn = pl.get("stage_name")
        if sn != _SELF_REFINEMENT_POLICY_STAGE:
            continue
        marker_count += 1
        if first_marker_occurred_at is None:
            first_marker_occurred_at = ev.get("occurred_at")
        last_marker_occurred_at = ev.get("occurred_at")
        version: Any = None
        description: Any = None
        eval_fields: dict[str, Any] = {}
        sr_promote: dict[str, Any] = {}
        max_iterations = None
        meta = ev.get("metadata")
        if isinstance(meta, dict):
            sr = meta.get("self_refinement")
            if isinstance(sr, dict):
                version = sr.get("version")
                description = sr.get("description")
                mi = sr.get("max_iterations")
                if isinstance(mi, int) and not isinstance(mi, bool) and mi >= 1:
                    max_iterations = mi
                evaluation = sr.get("evaluation")
                if isinstance(evaluation, dict):
                    status = evaluation.get("status")
                    if isinstance(status, str) and status.strip():
                        eval_fields["evaluation_status"] = status.strip()
                    gaps = evaluation.get("gaps")
                    if isinstance(gaps, list):
                        eval_fields["evaluation_gaps"] = gaps
                    promotion_ready = evaluation.get("promotion_ready")
                    if isinstance(promotion_ready, bool):
                        eval_fields["promotion_ready"] = promotion_ready
                    cov = evaluation.get("coverage")
                    if isinstance(cov, dict):
                        ba = cov.get("business_area")
                        if isinstance(ba, dict) and isinstance(ba.get("id"), str):
                            eval_fields["coverage_business_area_id"] = ba["id"]
                        dr = cov.get("development_role")
                        if isinstance(dr, dict) and isinstance(dr.get("id"), str):
                            eval_fields["coverage_development_role_id"] = dr["id"]
                np = sr.get("auto_promote_probation")
                if isinstance(np, dict) and np:
                    sr_promote = dict(np)
                llm_critique = sr.get("llm_critique")
                if isinstance(llm_critique, dict):
                    llm_summary = llm_critique.get("summary")
                    if isinstance(llm_summary, str) and llm_summary.strip():
                        eval_fields["llm_critique_summary"] = llm_summary.strip()
                ungated = sr.get("ungated_loop")
                if isinstance(ungated, bool):
                    eval_fields["ungated_loop"] = ungated
                prv = sr.get("prior_gate_verdict")
                if isinstance(prv, str) and prv.strip():
                    eval_fields["prior_gate_verdict"] = prv.strip().upper()
        out = {
            "event_id": ev.get("event_id"),
            "occurred_at": ev.get("occurred_at"),
            "stage_name": sn,
            "attempt": pl.get("attempt"),
            "version": version,
            "description": description,
        }
        if max_iterations is not None:
            out["max_iterations"] = max_iterations
        if eval_fields:
            out.update(eval_fields)
        if sr_promote:
            out["auto_promote"] = sr_promote
            req = sr_promote.get("auto_promote_probation_requested")
            if isinstance(req, bool):
                out["auto_promote_requested"] = req
            applied = sr_promote.get("auto_promote_probation_applied")
            if isinstance(applied, bool):
                out["auto_promote_applied"] = applied
            reason = sr_promote.get("reason")
            if isinstance(reason, str) and reason.strip():
                out["auto_promote_reason"] = reason.strip()
    if out is None:
        return None
    loop_signal_count = 0
    ungated_iteration_count = 0
    phase_d_signal: dict[str, Any] | None = None
    for ev in events:
        if ev.get("event_type") != EventType.SELF_REFINEMENT_LOOP_SIGNALLED.value:
            continue
        loop_signal_count += 1
        payload = ev.get("payload")
        signal_pl: dict[str, Any] = payload if isinstance(payload, dict) else {}
        if signal_pl.get("signal") == "phase_d_iteration":
            ungated_iteration_count += 1
        phase_d_signal = {
            "event_id": ev.get("event_id"),
            "occurred_at": ev.get("occurred_at"),
            "phase": signal_pl.get("phase"),
            "signal": signal_pl.get("signal"),
            "attempt": signal_pl.get("attempt"),
            "max_iterations": signal_pl.get("max_iterations"),
            "gate_decision": signal_pl.get("gate_decision"),
            "evaluation_status": signal_pl.get("evaluation_status"),
            "loops_remaining": signal_pl.get("loops_remaining"),
            "iteration_progress_ratio": signal_pl.get("iteration_progress_ratio"),
            "should_continue": signal_pl.get("should_continue"),
            "orchestration_branch": signal_pl.get("orchestration_branch"),
            "llm_critique_enabled": signal_pl.get("llm_critique_enabled"),
            "llm_critique_attempted": signal_pl.get("llm_critique_attempted"),
            "llm_critique_verdict": signal_pl.get("llm_critique_verdict"),
            "llm_gate_decision": signal_pl.get("llm_gate_decision"),
        }
    if loop_signal_count > 0:
        out["loop_signal_count"] = loop_signal_count
        if out.get("ungated_loop") is True and ungated_iteration_count > 0:
            out["ungated_iteration_count"] = ungated_iteration_count
    if phase_d_signal is not None:
        out["phase_d_signal"] = phase_d_signal
        for key in (
            "gate_decision",
            "loops_remaining",
            "iteration_progress_ratio",
            "should_continue",
            "orchestration_branch",
        ):
            if phase_d_signal.get(key) is not None:
                out[key] = phase_d_signal.get(key)
    llm_critique_stage: dict[str, Any] | None = None
    for stage_row in reversed(universal_critique_timeline_entries(events)):
        if stage_row.get("stage_name") == "self_refinement.critique":
            llm_critique_stage = dict(stage_row)
            break
    if llm_critique_stage is not None:
        out["llm_critique_stage"] = llm_critique_stage
    out["marker_count"] = marker_count
    if first_marker_occurred_at is not None:
        out["first_marker_occurred_at"] = first_marker_occurred_at
    if last_marker_occurred_at is not None:
        out["last_marker_occurred_at"] = last_marker_occurred_at
    if max_iterations is not None:
        out["max_iterations_exceeded"] = any(
            ev.get("event_type") == EventType.STAGE_FAILED.value
            and (ev.get("payload") or {}).get("reason_code") == "self_refinement_max_iterations"
            for ev in events
        )
    return out


def _self_refinement_marker_row_from_event(ev: dict[str, Any]) -> dict[str, Any] | None:
    payload = ev.get("payload")
    pl: dict[str, Any] = payload if isinstance(payload, dict) else {}
    if pl.get("stage_name") != _SELF_REFINEMENT_POLICY_STAGE:
        return None
    version: Any = None
    meta = ev.get("metadata")
    if isinstance(meta, dict):
        sr = meta.get("self_refinement")
        if isinstance(sr, dict):
            version = sr.get("version")
    return {
        "event_id": ev.get("event_id"),
        "occurred_at": ev.get("occurred_at"),
        "version": version,
    }


def self_refinement_marker_timeline_entries(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Chronological ``self_refinement:policy`` markers (``store_seq`` order)."""
    want = EventType.STAGE_STARTED.value
    hist: list[dict[str, Any]] = []
    for ev in events:
        if ev.get("event_type") != want:
            continue
        row = _self_refinement_marker_row_from_event(ev)
        if row is not None:
            hist.append(row)
    return hist


def self_refinement_marker_timeline_history(
    events: list[dict[str, Any]],
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Bounded self-refinement marker history for operator drill-down."""
    hist = self_refinement_marker_timeline_entries(events)
    if not hist:
        return []
    if len(hist) <= limit:
        return hist
    return hist[-limit:]


__all__ = [
    "SELF_REFINEMENT_SUMMARY_KEYS",
    "self_refinement_marker_timeline_entries",
    "self_refinement_marker_timeline_history",
    "self_refinement_timeline_summary",
]
