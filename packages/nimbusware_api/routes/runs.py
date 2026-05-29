from __future__ import annotations

import base64
import binascii
import json
import os
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlencode
from uuid import UUID

from fastapi import Header, HTTPException, Query, Request, Response
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

from agent_core.models import EventType, serialize_event_persistent, validate_event_dict
from nimbusware_api.deps import OrchDep, StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.preflight_read_model import preflight_timeline_summary
from nimbusware_api.schemas.openapi import (
    CREATE_RUN_RESPONSE_200,
    CREATE_RUN_RESPONSE_422,
    PROBLEM_RESPONSE_404,
    PROBLEM_RESPONSE_422,
    PROBLEM_RESPONSE_500,
    RUN_DETAIL_LINK_HEADER,
    RUN_FINDINGS_LINK_HEADER,
    RUN_LIST_LINK_HEADER,
    RUN_TIMELINE_RESPONSE_200,
    format_run_detail_link_header,
    format_run_findings_link_header,
    format_run_timeline_link_header,
)
from nimbusware_api.schemas.runs import (
    RunDetailResponse,
    RunListResponse,
    RunSummary,
    RunTimelineResponse,
)
from hermes_extensions.phase2 import agent_evaluator_score_band
from hermes_orchestrator.default_workflow_profile import default_workflow_profile
from hermes_orchestrator.critic_matrix_live import (
    build_live_critic_matrix_rows,
    critic_matrix_unanimous_summary,
)
from hermes_orchestrator.critique_routing import CRITIQUE_STAGE_TO_PRODUCER
from hermes_orchestrator.llm_plan import (
    IMPLEMENTATION_CRITIQUE_STAGE,
    TEST_WRITER_CRITIQUE_STAGE,
)
from hermes_orchestrator.read_models import (
    RUN_LIST_FILTER_STATUSES,
    build_run_summary,
    critique_coverage_from_run_created_metadata,
    persona_assignment_from_run_created_metadata,
)
from hermes_orchestrator.stage_graph import stage_graph_timeline_summary_from_metadata
from hermes_store.protocol import serialized_event_from_row

router = APIRouter(tags=["runs"])

# When ``include_summary=1``, list page size must stay small to avoid N+1 load.
INCLUDE_SUMMARY_MAX_LIMIT = 20

# Timeline summary emission policy (additive / presence-gated):
# - Integrator gate rows omit ranking/selection keys unless present in metadata.
# - Self-refinement omits ``max_iterations`` / ``max_iterations_exceeded`` unless
#   ``max_iterations`` is a positive int on the policy marker metadata.
# - Helpers diverge on skip-vs-emit for degraded metadata (see fo112 quintet tests);
#   do not unify integrator-gate skip logic with self-refinement emit-on-missing-meta.


def _integrator_gate_row_from_event(ev: dict[str, Any]) -> dict[str, Any]:
    """Shape one timeline row from a ``gate.decision.emitted`` event (caller filters type).

    Ranking/selection keys are presence-gated from metadata (see module policy above).
    """
    meta = ev.get("metadata")
    meta_d = meta if isinstance(meta, dict) else {}
    payload = ev.get("payload")
    pl: dict[str, Any] = payload if isinstance(payload, dict) else {}
    out = {
        "event_id": ev.get("event_id"),
        "occurred_at": ev.get("occurred_at"),
        "stage_name": pl.get("stage_name"),
        "verdict": pl.get("verdict"),
        "failure_reason_code": pl.get("failure_reason_code"),
        "bundle_id": meta_d.get("bundle_id"),
        "bundle_title": meta_d.get("bundle_title"),
        "integrator_score": meta_d.get("integrator_score"),
        "min_score_to_pass": meta_d.get("min_score_to_pass"),
        "integrator_project_tags": meta_d.get("integrator_project_tags"),
        "integrator_bundle_tags": meta_d.get("integrator_bundle_tags"),
        "integrator_matched_tags": meta_d.get("integrator_matched_tags"),
    }
    if "bundle_compatibility_ranking" in meta_d:
        out["bundle_compatibility_ranking"] = meta_d.get("bundle_compatibility_ranking")
    if "bundle_compatibility_ranking_count" in meta_d:
        out["bundle_compatibility_ranking_count"] = meta_d.get(
            "bundle_compatibility_ranking_count"
        )
    if "selected_bundle_rank" in meta_d:
        out["selected_bundle_rank"] = meta_d.get("selected_bundle_rank")
    if "bundle_id" in meta_d and (
        "bundle_compatibility_ranking" in meta_d
        or "bundle_compatibility_ranking_count" in meta_d
        or "selected_bundle_rank" in meta_d
    ):
        out["selected_bundle_id"] = meta_d.get("bundle_id")
    return out


def integrator_gate_timeline_entries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chronological integrator gate decisions (presence-gated rows per event)."""
    want = EventType.GATE_DECISION_EMITTED.value
    hist: list[dict[str, Any]] = []
    for ev in events:
        if ev.get("event_type") != want:
            continue
        meta = ev.get("metadata")
        if not isinstance(meta, dict) or meta.get("integrator_gate") is not True:
            continue
        hist.append(_integrator_gate_row_from_event(ev))
    return hist


def integrator_gate_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest integrator gate decision; row uses presence-gated optional keys (module policy)."""
    hist = integrator_gate_timeline_entries(events)
    return hist[-1] if hist else None


def integrator_gate_timeline_history(
    events: list[dict[str, Any]],
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Bounded integrator gate history for operator drill-down (latest entries win when trimmed)."""
    hist = integrator_gate_timeline_entries(events)
    if not hist:
        return []
    if len(hist) <= limit:
        return hist
    return hist[-limit:]


def _integrator_score_delta(prev: Any, cur: Any) -> float | None:
    try:
        a = float(prev) if prev is not None else None
        b = float(cur) if cur is not None else None
    except (TypeError, ValueError):
        return None
    if a is None or b is None:
        return None
    return round(b - a, 6)


def integrator_gate_timeline_delta(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest integrator gate vs the immediately prior gate (needs at least two decisions)."""
    hist = integrator_gate_timeline_entries(events)
    if len(hist) < 2:
        return None
    prev, cur = hist[-2], hist[-1]
    return {
        "previous_event_id": prev.get("event_id"),
        "current_event_id": cur.get("event_id"),
        "integrator_score_delta": _integrator_score_delta(
            prev.get("integrator_score"),
            cur.get("integrator_score"),
        ),
        "verdict_changed": prev.get("verdict") != cur.get("verdict"),
        "bundle_id_changed": prev.get("bundle_id") != cur.get("bundle_id"),
        "min_score_to_pass": cur.get("min_score_to_pass"),
        "previous_verdict": prev.get("verdict"),
        "current_verdict": cur.get("verdict"),
    }


def persona_assignment_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Frozen composite persona from first ``run.created`` (same as run summary)."""
    want = EventType.RUN_CREATED.value
    for ev in events:
        if ev.get("event_type") != want:
            continue
        meta = ev.get("metadata")
        if not isinstance(meta, dict):
            return None
        return persona_assignment_from_run_created_metadata(meta)
    return None


_AGENT_EVAL_STAGE_PREFIX = "agent_eval:"


def _agent_evaluator_bool_field(block: dict[str, Any], *keys: str) -> bool | None:
    for key in keys:
        val = block.get(key)
        if isinstance(val, bool):
            return val
    return None


def _agent_evaluator_str_field(block: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        val = block.get(key)
        if isinstance(val, str):
            text = val.strip()
            if text:
                return text
    return None


def _apply_agent_evaluator_flat_auto_actions(
    out: dict[str, Any],
    *,
    ae_promote: dict[str, Any],
    ae_create: dict[str, Any],
) -> None:
    """Add top-level scalar auto-promote / auto-create fields for operator tables."""
    if ae_promote:
        req = _agent_evaluator_bool_field(
            ae_promote,
            "auto_promote_probation_requested",
            "auto_promote_requested",
        )
        if req is not None:
            out["auto_promote_requested"] = req
        applied = _agent_evaluator_bool_field(
            ae_promote,
            "auto_promote_probation_applied",
            "auto_promote_applied",
        )
        if applied is not None:
            out["auto_promote_applied"] = applied
        reason = _agent_evaluator_str_field(ae_promote, "reason")
        if reason is not None:
            out["auto_promote_reason"] = reason
    if ae_create:
        req = _agent_evaluator_bool_field(
            ae_create,
            "auto_create_persona_requested",
            "auto_create_requested",
        )
        if req is not None:
            out["auto_create_requested"] = req
        applied = _agent_evaluator_bool_field(
            ae_create,
            "auto_create_persona_applied",
            "auto_create_applied",
        )
        if applied is not None:
            out["auto_create_applied"] = applied
        reason = _agent_evaluator_str_field(ae_create, "reason")
        if reason is not None:
            out["auto_create_reason"] = reason
        shelf = _agent_evaluator_str_field(ae_create, "shelf")
        if shelf is not None:
            out["auto_create_shelf"] = shelf
        display = _agent_evaluator_str_field(ae_create, "display_name")
        if display is not None:
            out["auto_create_display_name"] = display


def agent_evaluator_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest agent-evaluator stage marker (``agent_eval:*`` prefix gate)."""
    out: dict[str, Any] | None = None
    want = EventType.STAGE_STARTED.value
    for ev in events:
        if ev.get("event_type") != want:
            continue
        payload = ev.get("payload")
        pl: dict[str, Any] = payload if isinstance(payload, dict) else {}
        sn = pl.get("stage_name")
        if not isinstance(sn, str) or not sn.startswith(_AGENT_EVAL_STAGE_PREFIX):
            continue
        suffix = sn[len(_AGENT_EVAL_STAGE_PREFIX) :]
        persona_id: str | None = suffix if suffix else None
        ae_promote: dict[str, Any] = {}
        ae_create: dict[str, Any] = {}
        meta = ev.get("metadata")
        if isinstance(meta, dict):
            inner = meta.get("agent_evaluator")
            if isinstance(inner, dict):
                np = inner.get("auto_promote_probation")
                nc = inner.get("auto_create_persona")
                if isinstance(np, dict) or isinstance(nc, dict):
                    if isinstance(np, dict) and np:
                        ae_promote = dict(np)
                    if isinstance(nc, dict) and nc:
                        ae_create = dict(nc)
                elif inner:
                    ae_promote = dict(inner)
        out = {
            "event_id": ev.get("event_id"),
            "occurred_at": ev.get("occurred_at"),
            "stage_name": sn,
            "persona_id": persona_id,
            "attempt": pl.get("attempt"),
        }
        if ae_promote:
            out["auto_promote"] = ae_promote
        if ae_create:
            out["auto_create_persona"] = ae_create
        _apply_agent_evaluator_flat_auto_actions(
            out,
            ae_promote=ae_promote,
            ae_create=ae_create,
        )
        evaluation: dict[str, Any] | None = None
        if isinstance(meta, dict):
            inner = meta.get("agent_evaluator")
            if isinstance(inner, dict):
                evl = inner.get("evaluation")
                if isinstance(evl, dict):
                    evaluation = evl
        if evaluation:
            status = evaluation.get("status")
            if isinstance(status, str) and status.strip():
                out["evaluation_status"] = status.strip()
            score = evaluation.get("score")
            if isinstance(score, (int, float)) and not isinstance(score, bool):
                score_f = float(score)
                out["evaluation_score"] = score_f
                out["evaluation_score_band"] = agent_evaluator_score_band(score_f)
            cov_ratio = evaluation.get("coverage_ratio")
            if isinstance(cov_ratio, (int, float)) and not isinstance(cov_ratio, bool):
                out["coverage_ratio"] = float(cov_ratio)
            promotion_ready = evaluation.get("promotion_ready")
            if isinstance(promotion_ready, bool):
                out["promotion_ready"] = promotion_ready
            gaps = evaluation.get("gaps")
            if isinstance(gaps, list):
                out["evaluation_gaps"] = gaps
            cov = evaluation.get("coverage")
            if isinstance(cov, dict):
                ba = cov.get("business_area")
                if isinstance(ba, dict) and isinstance(ba.get("id"), str):
                    out["coverage_business_area_id"] = ba["id"]
                dr = cov.get("development_role")
                if isinstance(dr, dict) and isinstance(dr.get("id"), str):
                    out["coverage_development_role_id"] = dr["id"]
        if isinstance(meta, dict):
            inner = meta.get("agent_evaluator")
            if isinstance(inner, dict):
                branch = inner.get("evaluation_branch")
                if isinstance(branch, str) and branch.strip():
                    out["evaluation_branch"] = branch.strip()
                mode = inner.get("production_scoring_mode")
                if isinstance(mode, str) and mode.strip():
                    out["production_scoring_mode"] = mode.strip()
                llm_eval = inner.get("llm_evaluation")
                if isinstance(llm_eval, dict):
                    llm_mode = llm_eval.get("production_scoring_mode")
                    if isinstance(llm_mode, str) and llm_mode.strip():
                        out["llm_production_scoring_mode"] = llm_mode.strip()
                    summary = llm_eval.get("summary")
                    if isinstance(summary, str) and summary.strip():
                        out["llm_evaluation_summary"] = summary.strip()
                    llm_status = llm_eval.get("status")
                    if isinstance(llm_status, str) and llm_status.strip():
                        out["llm_evaluation_status"] = llm_status.strip()
                    policy_score = llm_eval.get("policy_score")
                    if isinstance(policy_score, (int, float)) and not isinstance(
                        policy_score,
                        bool,
                    ):
                        ps_f = float(policy_score)
                        out["llm_evaluation_score"] = ps_f
                        band_raw = llm_eval.get("policy_score_band")
                        if isinstance(band_raw, str) and band_raw.strip():
                            out["llm_evaluation_score_band"] = band_raw.strip()
                        else:
                            out["llm_evaluation_score_band"] = agent_evaluator_score_band(
                                ps_f,
                            )
    gate_verdict: str | None = None
    coverage_branch: str | None = None
    coverage_summary: str | None = None
    for ev in events:
        if ev.get("event_type") == EventType.STAGE_STARTED.value:
            pl2 = ev.get("payload")
            if isinstance(pl2, dict) and pl2.get("stage_name") == "agent_evaluator.critique":
                meta2 = ev.get("metadata")
                if isinstance(meta2, dict):
                    ae2 = meta2.get("agent_evaluator")
                    if isinstance(ae2, dict):
                        br = ae2.get("persona_coverage_critique_branch")
                        sm = ae2.get("llm_summary")
                        if isinstance(br, str) and br.strip():
                            coverage_branch = br.strip()
                        if isinstance(sm, str) and sm.strip():
                            coverage_summary = sm.strip()
        if ev.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
            continue
        pl = ev.get("payload")
        if not isinstance(pl, dict):
            continue
        if pl.get("stage_name") == "agent_evaluator.critique":
            v = pl.get("verdict")
            if v is not None:
                gate_verdict = str(v).strip().upper()
    if gate_verdict:
        out = out or {}
        out["critique_gate_verdict"] = gate_verdict
    if coverage_branch:
        out = out or {}
        out["persona_coverage_critique_branch"] = coverage_branch
    if coverage_summary:
        out = out or {}
        out["persona_coverage_llm_summary"] = coverage_summary
    return out


_SELF_REFINEMENT_POLICY_STAGE = "self_refinement:policy"


def self_refinement_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest ``stage.started`` with ``self_refinement:policy`` (self-refinement marker).

    ``marker_count`` is the total number of such markers in the run (including repeats —
    the orchestrator does not dedupe self-refinement stage markers).

    ``first_marker_occurred_at`` is the ``occurred_at`` of the **first** such marker in
    append order (when ``marker_count`` is 0 this field is omitted).

    ``last_marker_occurred_at`` is the ``occurred_at`` of the **last** such marker in
    append order (omitted when there are no markers; equals ``first_marker_occurred_at``
    when exactly one marker exists).

    ``max_iterations`` / ``max_iterations_exceeded`` follow module presence-gated policy.
    """
    out: dict[str, Any] | None = None
    marker_count = 0
    first_marker_occurred_at: Any = None
    last_marker_occurred_at: Any = None
    want = EventType.STAGE_STARTED.value
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
        max_iterations: Any = None
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
        pl: dict[str, Any] = payload if isinstance(payload, dict) else {}
        if pl.get("signal") == "phase_d_iteration":
            ungated_iteration_count += 1
        phase_d_signal = {
            "event_id": ev.get("event_id"),
            "occurred_at": ev.get("occurred_at"),
            "phase": pl.get("phase"),
            "signal": pl.get("signal"),
            "attempt": pl.get("attempt"),
            "max_iterations": pl.get("max_iterations"),
            "gate_decision": pl.get("gate_decision"),
            "evaluation_status": pl.get("evaluation_status"),
            "loops_remaining": pl.get("loops_remaining"),
            "iteration_progress_ratio": pl.get("iteration_progress_ratio"),
            "should_continue": pl.get("should_continue"),
            "orchestration_branch": pl.get("orchestration_branch"),
            "llm_critique_enabled": pl.get("llm_critique_enabled"),
            "llm_critique_attempted": pl.get("llm_critique_attempted"),
            "llm_critique_verdict": pl.get("llm_critique_verdict"),
            "llm_gate_decision": pl.get("llm_gate_decision"),
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


def _run_escalated_row_from_event(ev: dict[str, Any]) -> dict[str, Any]:
    """Shape one timeline row from a ``run.escalated`` event."""
    payload = ev.get("payload")
    pl: dict[str, Any] = payload if isinstance(payload, dict) else {}
    return {
        "event_id": ev.get("event_id"),
        "occurred_at": ev.get("occurred_at"),
        "actor_id": pl.get("actor_id"),
        "reason_code": pl.get("reason_code"),
        "policy_snapshot_id": pl.get("policy_snapshot_id"),
        "notes": pl.get("notes"),
    }


def run_escalated_timeline_entries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chronological ``run.escalated`` events (``store_seq`` order of ``events``)."""
    want = EventType.RUN_ESCALATED.value
    hist: list[dict[str, Any]] = []
    for ev in events:
        if ev.get("event_type") != want:
            continue
        hist.append(_run_escalated_row_from_event(ev))
    return hist


def run_escalated_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest ``run.escalated`` event summary (human / system escalation checkpoint)."""
    hist = run_escalated_timeline_entries(events)
    return hist[-1] if hist else None


def run_escalated_timeline_history(
    events: list[dict[str, Any]],
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Bounded run escalation history for operator drill-down."""
    hist = run_escalated_timeline_entries(events)
    if not hist:
        return []
    if len(hist) <= limit:
        return hist
    return hist[-limit:]


def run_escalated_timeline_delta(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest escalation vs the immediately prior (needs at least two events)."""
    hist = run_escalated_timeline_entries(events)
    if len(hist) < 2:
        return None
    prev, cur = hist[-2], hist[-1]
    return {
        "previous_event_id": prev.get("event_id"),
        "current_event_id": cur.get("event_id"),
        "reason_code_changed": prev.get("reason_code") != cur.get("reason_code"),
        "actor_id_changed": prev.get("actor_id") != cur.get("actor_id"),
        "policy_snapshot_id_changed": prev.get("policy_snapshot_id")
        != cur.get("policy_snapshot_id"),
        "previous_reason_code": prev.get("reason_code"),
        "current_reason_code": cur.get("reason_code"),
        "previous_actor_id": prev.get("actor_id"),
        "current_actor_id": cur.get("actor_id"),
    }


_CRITIQUE_STAGE_ORDER: tuple[str, ...] = (
    "planner.critique",
    "implementation.critique",
    "test_writer.critique",
    "frontend_writer.critique",
    "module_integrator.critique",
    "agent_evaluator.critique",
    "self_refinement.critique",
)


def _critique_row_from_gate_event(ev: dict[str, Any]) -> dict[str, Any] | None:
    payload = ev.get("payload")
    pl: dict[str, Any] = payload if isinstance(payload, dict) else {}
    sn = pl.get("stage_name")
    if not isinstance(sn, str) or not sn.endswith(".critique"):
        return None
    meta = ev.get("metadata")
    meta_d = meta if isinstance(meta, dict) else {}
    if meta_d.get("integrator_gate") is True:
        return None
    row = {
        "event_id": ev.get("event_id"),
        "occurred_at": ev.get("occurred_at"),
        "stage_name": sn,
        "verdict": pl.get("verdict"),
        "failure_reason_code": pl.get("failure_reason_code"),
    }
    failing = pl.get("failing_critics")
    if isinstance(failing, list) and failing:
        row["failing_critics"] = [str(x) for x in failing]
    producer = CRITIQUE_STAGE_TO_PRODUCER.get(sn)
    if producer is not None:
        row["producer_taxonomy_key"] = producer
    return row


def universal_critique_timeline_entries(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Latest ``gate.decision.emitted`` per universal-critique stage (chronological scan)."""
    want = EventType.GATE_DECISION_EMITTED.value
    by_stage: dict[str, dict[str, Any]] = {}
    for ev in events:
        if ev.get("event_type") != want:
            continue
        row = _critique_row_from_gate_event(ev)
        if row is None:
            continue
        sn = row["stage_name"]
        if isinstance(sn, str):
            by_stage[sn] = row
    ordered: list[dict[str, Any]] = []
    for name in _CRITIQUE_STAGE_ORDER:
        if name in by_stage:
            ordered.append(by_stage[name])
    for name in sorted(by_stage.keys()):
        if name not in _CRITIQUE_STAGE_ORDER:
            ordered.append(by_stage[name])
    return ordered


def universal_critique_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Rollup of latest universal-critique gate decisions on the run."""
    stages = universal_critique_timeline_entries(events)
    if not stages:
        return None
    out: dict[str, Any] = {
        "stages": stages,
        "stage_count": len(stages),
        "fail_count": 0,
        "pass_count": 0,
        "distinct_fail_stages": [],
    }
    fail_count = 0
    pass_count = 0
    fail_stage_names: list[str] = []
    for s in stages:
        v = s.get("verdict")
        verdict = str(v).strip().upper() if v is not None else ""
        if verdict == "FAIL":
            fail_count += 1
            stage_name = s.get("stage_name")
            if isinstance(stage_name, str) and stage_name.strip():
                fail_stage_names.append(stage_name.strip())
        elif verdict == "PASS":
            pass_count += 1
    out["fail_count"] = fail_count
    out["pass_count"] = pass_count
    stage_count = len(stages)
    if stage_count > 0:
        out["fail_rate"] = round(fail_count / stage_count, 4)
    out["distinct_fail_stages"] = sorted(set(fail_stage_names))
    critique_coverage: dict[str, Any] | None = None
    for ev in events:
        if ev.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = ev.get("metadata")
        if isinstance(meta, dict):
            critique_coverage = critique_coverage_from_run_created_metadata(meta)
        break
    if critique_coverage is not None:
        out["critique_coverage"] = critique_coverage
    for ev in events:
        if ev.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = ev.get("metadata")
        if isinstance(meta, dict):
            uce = universal_critique_effective_from_run_created_metadata(meta)
            if uce is not None:
                if isinstance(uce.get("unanimous_gate_enforce"), bool):
                    out["unanimous_gate_effective"] = uce["unanimous_gate_enforce"]
                if isinstance(uce.get("default_enabled"), bool):
                    out["default_enabled_effective"] = uce["default_enabled"]
                if isinstance(uce.get("production_default_on"), bool):
                    out["production_default_on"] = uce["production_default_on"]
        break
    return out


def stage_graph_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Compact stage DAG rollup from frozen ``run.created`` ``metadata.stage_graph``."""
    for ev in events:
        if ev.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = ev.get("metadata")
        if isinstance(meta, dict):
            return stage_graph_timeline_summary_from_metadata(meta)
        break
    return None


_WRITER_GATE_STAGE: dict[str, str] = {
    "implementation": IMPLEMENTATION_CRITIQUE_STAGE,
    "test_writer": TEST_WRITER_CRITIQUE_STAGE,
    "frontend_writer": "frontend_writer.critique",
}


def parallel_writer_groups_timeline_summary(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Roll up parallel writer groups with gate pass/fail per mapped critique stage."""
    stage_graph_meta: dict[str, Any] | None = None
    for ev in events:
        if ev.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = ev.get("metadata")
        if isinstance(meta, dict):
            sg = meta.get("stage_graph")
            stage_graph_meta = sg if isinstance(sg, dict) else None
        break
    if not stage_graph_meta:
        return None
    parallel_groups = stage_graph_meta.get("parallel_groups")
    if not isinstance(parallel_groups, dict) or not parallel_groups:
        return None
    gate_verdict: dict[str, str] = {}
    for ev in events:
        if ev.get("event_type") != EventType.GATE_DECISION_EMITTED.value:
            continue
        pl = ev.get("payload")
        if not isinstance(pl, dict):
            continue
        sn = pl.get("stage_name")
        if isinstance(sn, str) and sn.strip():
            verdict_raw = pl.get("verdict")
            gate_verdict[sn.strip()] = (
                str(verdict_raw).strip().upper() if verdict_raw is not None else ""
            )

    stage_started: dict[str, dict[str, Any]] = {}
    stage_passed: dict[str, dict[str, Any]] = {}
    stage_failed: dict[str, dict[str, Any]] = {}
    dispatch_mode = "sequential"
    for ev in events:
        et = ev.get("event_type")
        pl = ev.get("payload")
        if not isinstance(pl, dict):
            continue
        sn_raw = pl.get("stage_name")
        if not isinstance(sn_raw, str):
            continue
        sn = sn_raw.strip()
        meta = ev.get("metadata") if isinstance(ev.get("metadata"), dict) else {}
        if et == EventType.STAGE_STARTED.value and sn in (
            "implementation",
            "test_writer",
            "frontend_writer",
        ):
            stage_started[sn] = {
                "occurred_at": ev.get("occurred_at"),
                "dispatch_mode": meta.get("dispatch_mode"),
                "body_mode": meta.get("body_mode"),
            }
            dm = meta.get("dispatch_mode")
            if isinstance(dm, str) and dm.strip():
                dispatch_mode = dm.strip().lower()
        elif et == EventType.STAGE_PASSED.value and sn in (
            "implementation",
            "test_writer",
            "frontend_writer",
        ):
            stage_passed[sn] = {
                "duration_ms": pl.get("duration_ms"),
                "occurred_at": ev.get("occurred_at"),
                "exit_code": meta.get("exit_code"),
                "body_mode": meta.get("body_mode"),
            }
        elif et == EventType.STAGE_FAILED.value and sn in (
            "implementation",
            "test_writer",
            "frontend_writer",
        ):
            stage_failed[sn] = {
                "occurred_at": ev.get("occurred_at"),
                "failure_reason": meta.get("failure_reason") or pl.get("reason_code"),
                "exit_code": meta.get("exit_code"),
                "body_mode": meta.get("body_mode"),
            }

    out: list[dict[str, Any]] = []
    for group_id, stages in parallel_groups.items():
        if not isinstance(stages, list):
            continue
        gate_pass: list[str] = []
        gate_fail: list[str] = []
        stage_details: list[dict[str, Any]] = []
        for stage in stages:
            stage_key = str(stage)
            critique_stage = _WRITER_GATE_STAGE.get(stage_key, stage_key)
            verdict = gate_verdict.get(critique_stage, "")
            if verdict == "PASS":
                gate_pass.append(stage_key)
            elif verdict == "FAIL":
                gate_fail.append(stage_key)
            detail: dict[str, Any] = {"stage_name": stage_key}
            if stage_key in stage_started:
                detail["started_at"] = stage_started[stage_key].get("occurred_at")
                if stage_started[stage_key].get("body_mode") is not None:
                    detail["body_mode"] = stage_started[stage_key].get("body_mode")
            if stage_key in stage_passed:
                detail["passed"] = True
                detail["duration_ms"] = stage_passed[stage_key].get("duration_ms")
                if stage_passed[stage_key].get("exit_code") is not None:
                    detail["exit_code"] = stage_passed[stage_key].get("exit_code")
                if stage_passed[stage_key].get("body_mode") is not None:
                    detail["body_mode"] = stage_passed[stage_key].get("body_mode")
            elif stage_key in stage_failed:
                detail["passed"] = False
                if stage_failed[stage_key].get("exit_code") is not None:
                    detail["exit_code"] = stage_failed[stage_key].get("exit_code")
                if stage_failed[stage_key].get("failure_reason") is not None:
                    detail["failure_reason"] = stage_failed[stage_key].get("failure_reason")
                if stage_failed[stage_key].get("body_mode") is not None:
                    detail["body_mode"] = stage_failed[stage_key].get("body_mode")
            else:
                detail["passed"] = stage_key in stage_passed
            stage_details.append(detail)
        out.append(
            {
                "group_id": str(group_id),
                "stages": [str(s) for s in stages],
                "dispatch_mode": dispatch_mode,
                "stage_details": stage_details,
                "gate_pass": gate_pass,
                "gate_fail": gate_fail,
            },
        )
    return out or None


def critic_matrix_live_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Live orchestration critic matrix (gate decisions + pending critique stages)."""
    rows = build_live_critic_matrix_rows(events)
    if not rows:
        return None
    summary = critic_matrix_unanimous_summary(rows)
    return {"rows": rows, "summary": summary}


def universal_critique_effective_from_run_created_metadata(
    metadata: Mapping[str, Any] | dict[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(metadata, Mapping):
        return None
    raw = metadata.get("universal_critique_effective")
    return dict(raw) if isinstance(raw, dict) else None


def _finding_has_security_scan_metadata(meta: Any) -> bool:
    if not isinstance(meta, dict):
        return False
    return "security_scan_exit" in meta or "security_scan_snippet" in meta


def _security_scan_row_from_event(ev: dict[str, Any]) -> dict[str, Any] | None:
    meta = ev.get("metadata")
    if not _finding_has_security_scan_metadata(meta):
        return None
    m: dict[str, Any] = meta if isinstance(meta, dict) else {}
    payload = ev.get("payload")
    pl: dict[str, Any] = payload if isinstance(payload, dict) else {}
    return {
        "event_id": ev.get("event_id"),
        "occurred_at": ev.get("occurred_at"),
        "finding_id": pl.get("finding_id"),
        "category": pl.get("category"),
        "severity": pl.get("severity"),
        "source_artifact": pl.get("source_artifact"),
        "security_scan_exit": m.get("security_scan_exit"),
        "security_scan_ruff_exit": m.get("security_scan_ruff_exit"),
        "security_scan_bandit_exit": m.get("security_scan_bandit_exit"),
        "security_scan_snippet": m.get("security_scan_snippet"),
    }


def security_scan_on_verify_timeline_entries(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Chronological security-scan ``finding.created`` rows (``store_seq`` order)."""
    want = EventType.FINDING_CREATED.value
    hist: list[dict[str, Any]] = []
    for ev in events:
        if ev.get("event_type") != want:
            continue
        row = _security_scan_row_from_event(ev)
        if row is not None:
            hist.append(row)
    return hist


def security_scan_on_verify_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest ``finding.created`` whose metadata carries verifier security scan fields."""
    hist = security_scan_on_verify_timeline_entries(events)
    return hist[-1] if hist else None


def security_scan_on_verify_timeline_history(
    events: list[dict[str, Any]],
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Bounded security-scan history for operator drill-down."""
    hist = security_scan_on_verify_timeline_entries(events)
    if not hist:
        return []
    if len(hist) <= limit:
        return hist
    return hist[-limit:]


_SCRAPER_FETCH_STAGE = "scraper:fetch"
_SCRAPER_FETCH_ROW_KEYS = (
    "url_host",
    "http_status",
    "bytes",
    "attempts",
    "content_length",
    "artifact_relpath",
)


def _scraper_fetch_row_sanitized(row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    out: dict[str, Any] = {}
    for key in _SCRAPER_FETCH_ROW_KEYS:
        if key not in row:
            continue
        val = row[key]
        if key in ("http_status", "bytes", "attempts", "content_length"):
            if isinstance(val, int) and not isinstance(val, bool):
                out[key] = val
        elif key == "artifact_relpath":
            if isinstance(val, str) and val.strip():
                out[key] = val.strip()
        elif key == "url_host":
            if isinstance(val, str) and val.strip():
                out[key] = val.strip()
    return out or None


def scraper_fetch_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest terminal ``scraper:fetch`` stage (``stage.passed`` or ``stage.failed``).

    Aggregates fetch rows from ``metadata.scraper_fetch.fetches`` when present.
  """
    out: dict[str, Any] | None = None
    passed_want = EventType.STAGE_PASSED.value
    failed_want = EventType.STAGE_FAILED.value
    for ev in events:
        et = ev.get("event_type")
        if et not in (passed_want, failed_want):
            continue
        payload = ev.get("payload")
        pl: dict[str, Any] = payload if isinstance(payload, dict) else {}
        sn = pl.get("stage_name")
        if sn != _SCRAPER_FETCH_STAGE:
            continue
        meta = ev.get("metadata")
        meta_d = meta if isinstance(meta, dict) else {}
        sf = meta_d.get("scraper_fetch")
        sf_d: dict[str, Any] = sf if isinstance(sf, dict) else {}
        fetches = sf_d.get("fetches")
        fetch_list = fetches if isinstance(fetches, list) else []
        fetch_count = 0
        total_bytes = 0
        for row in fetch_list:
            if not isinstance(row, dict):
                continue
            fetch_count += 1
            b = row.get("bytes")
            if isinstance(b, int) and not isinstance(b, bool):
                total_bytes += b
        outcome = "passed" if et == passed_want else "failed"
        out = {
            "event_id": ev.get("event_id"),
            "occurred_at": ev.get("occurred_at"),
            "outcome": outcome,
            "stage_name": sn,
            "fetch_count": fetch_count,
            "total_bytes": total_bytes,
        }
        host = sf_d.get("failed_url_host")
        if isinstance(host, str) and host.strip():
            out["failed_url_host"] = host.strip()
        if outcome == "failed":
            rc = pl.get("reason_code")
            if rc is not None:
                out["reason_code"] = str(rc)
            msg = pl.get("message")
            if msg is not None:
                out["message"] = str(msg)[:500]
        fetch_rows: list[dict[str, Any]] = []
        for row in fetch_list[:25]:
            sanitized = _scraper_fetch_row_sanitized(row)
            if sanitized is not None:
                fetch_rows.append(sanitized)
        if fetch_rows:
            out["fetches"] = fetch_rows
    return out


def _sanitize_workflow_profile_prefix(value: str | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    s = str(value).strip()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}", s):
        return None
    return s


def _encode_run_list_cursor(seq: int, run_id: UUID) -> str:
    raw = json.dumps({"s": seq, "r": str(run_id)}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_run_list_cursor(value: str) -> tuple[int, UUID]:
    pad = "=" * ((4 - len(value) % 4) % 4)
    raw = base64.urlsafe_b64decode(value + pad)
    d = json.loads(raw.decode())
    return int(d["s"]), UUID(str(d["r"]))


def _runs_list_query_string(
    *,
    limit: int,
    offset: int | None,
    order: str,
    include_summary: int,
    workflow_profile: str | None,
    workflow_profile_prefix: str | None,
    created_after: str | None,
    created_before: str | None,
    has_escalation: int | None,
    cursor: str | None = None,
    list_status: str | None = None,
) -> str:
    pairs: list[tuple[str, str]] = [
        ("limit", str(limit)),
        ("order", order),
        ("include_summary", str(include_summary)),
    ]
    if offset is not None:
        pairs.insert(1, ("offset", str(offset)))
    if cursor is not None:
        pairs.append(("cursor", cursor))
    if workflow_profile is not None:
        pairs.append(("workflow_profile", workflow_profile))
    if workflow_profile_prefix is not None:
        pairs.append(("workflow_profile_prefix", workflow_profile_prefix))
    if created_after is not None:
        pairs.append(("created_after", created_after))
    if created_before is not None:
        pairs.append(("created_before", created_before))
    if has_escalation is not None:
        pairs.append(("has_escalation", str(has_escalation)))
    if list_status is not None:
        pairs.append(("status", list_status))
    return urlencode(pairs)


def _parse_query_datetime(field: str, value: str | None) -> datetime | None:
    if value is None or not str(value).strip():
        return None
    try:
        s = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
    except ValueError as exc:
        msg = f"{field} must be a valid ISO-8601 datetime"
        raise ValueError(msg) from exc
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class CreateRunBody(BaseModel):
    workflow_profile: str = Field(default_factory=default_workflow_profile, min_length=1)
    business_area_persona_id: str | None = Field(default=None, max_length=200)
    development_role_persona_id: str | None = Field(default=None, max_length=200)
    custom_agent_id: str | None = Field(default=None, max_length=120)


@router.get(
    "/runs",
    response_model=RunListResponse,
    response_model_exclude_none=True,
    responses={
        200: {
            "description": "Recent run identifiers",
            "headers": {
                "Link": RUN_LIST_LINK_HEADER,
            },
            "content": {
                "application/json": {
                    "example": {
                        "run_ids": ["11111111-1111-4111-8111-111111111111"],
                        "total": 1,
                        "has_more": False,
                        "order": "newest_first",
                        "limit": 50,
                        "offset": 0,
                        "include_summary": 0,
                    },
                    "examples": {
                        "keyset_page": {
                            "summary": (
                                "cursor + next_cursor (offset 0; Link rel=next uses cursor=)"
                            ),
                            "value": {
                                "run_ids": ["11111111-1111-4111-8111-111111111111"],
                                "total": 50,
                                "has_more": True,
                                "order": "newest_first",
                                "limit": 1,
                                "offset": 0,
                                "include_summary": 0,
                                "next_cursor": (
                                    "eyJzIjoxMjM0LCJyIjoiMTExMTExMTEtMTExMS00MTExLTgxMTEtMTExMTExMTExMTExIn0"
                                ),
                            },
                        },
                        "with_summaries": {
                            "summary": "include_summary=1 (limit capped at 20)",
                            "value": {
                                "run_ids": ["11111111-1111-4111-8111-111111111111"],
                                "total": 1,
                                "has_more": False,
                                "order": "newest_first",
                                "limit": 10,
                                "offset": 0,
                                "include_summary": 1,
                                "summaries": {
                                    "11111111-1111-4111-8111-111111111111": {
                                        "status": "created",
                                        "workflow_profile": "default",
                                        "event_count": 1,
                                        "latest_event_type": "run.created",
                                        "terminal_event_type": None,
                                        "findings_count": 0,
                                        "has_escalation": False,
                                        "run_created_metadata": {},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def list_runs(
    request: Request,
    response: Response,
    store: StoreDep,
    limit: Annotated[int, Query(ge=1, le=200, description="Page size")] = 50,
    offset: Annotated[int, Query(ge=0, description="Offset into newest-first list")] = 0,
    workflow_profile: Annotated[
        str | None,
        Query(description="Filter by first run.created workflow_profile (case-insensitive)"),
    ] = None,
    created_after: Annotated[
        str | None,
        Query(
            description="ISO-8601 lower bound on first run.created occurred_at (inclusive, UTC)",
        ),
    ] = None,
    created_before: Annotated[
        str | None,
        Query(
            description="ISO-8601 upper bound on first run.created occurred_at (inclusive, UTC)",
        ),
    ] = None,
    workflow_profile_prefix: Annotated[
        str | None,
        Query(
            description=(
                "When ``workflow_profile`` is unset: case-insensitive prefix on first "
                "run.created workflow_profile (alphanumeric, dot, dash, underscore; max 64)"
            ),
        ),
    ] = None,
    order: Annotated[
        Literal["newest_first", "oldest_first"],
        Query(description="Sort by last store activity per run"),
    ] = "newest_first",
    include_summary: Annotated[
        int,
        Query(
            ge=0,
            le=1,
            description=(
                "When ``1``, include ``summaries`` keyed by run_id (max ``limit`` "
                f"{INCLUDE_SUMMARY_MAX_LIMIT}; request 422 if larger)"
            ),
        ),
    ] = 0,
    has_escalation: Annotated[
        int | None,
        Query(
            ge=0,
            le=1,
            description="When ``1``, only runs with a ``run.escalated`` event; ``0`` only without",
        ),
    ] = None,
    cursor: Annotated[
        str | None,
        Query(
            description=(
                "Opaque keyset cursor (from ``next_cursor``). When set, ``offset`` must be ``0``; "
                "ordering uses max ``store_seq`` per run plus ``run_id`` tiebreaker (same as "
                "offset pagination)."
            ),
        ),
    ] = None,
    status: Annotated[
        str | None,
        Query(
            description=(
                "Filter by replay-derived run status (same strings as run summaries): "
                "``created``, ``running``, or ``terminal``."
            ),
        ),
    ] = None,
) -> RunListResponse:
    lim = min(max(limit, 1), 200)
    off = max(offset, 0)
    if include_summary == 1 and lim > INCLUDE_SUMMARY_MAX_LIMIT:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "include_summary_limit_exceeded",
                f"include_summary=1 requires limit<={INCLUDE_SUMMARY_MAX_LIMIT}",
                details={"limit": lim, "max": INCLUDE_SUMMARY_MAX_LIMIT},
            ),
        )
    try:
        ca = _parse_query_datetime("created_after", created_after)
        cb = _parse_query_datetime("created_before", created_before)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_request",
                str(exc),
                details={"field": "created_after_or_created_before"},
            ),
        ) from exc
    wpfx = _sanitize_workflow_profile_prefix(workflow_profile_prefix)
    if workflow_profile is not None and workflow_profile_prefix is not None:
        wpfx = None
    esc_filter: bool | None = None if has_escalation is None else bool(has_escalation)
    raw_list_status = str(status).strip() if status is not None and str(status).strip() else None
    if raw_list_status is not None and raw_list_status not in RUN_LIST_FILTER_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_request",
                "status must be one of: created, running, terminal",
                details={"status": raw_list_status, "allowed": sorted(RUN_LIST_FILTER_STATUSES)},
            ),
        )
    list_status_filter: str | None = raw_list_status
    use_cursor = cursor is not None and str(cursor).strip() != ""
    if use_cursor and off != 0:
        raise HTTPException(
            status_code=422,
            detail=problem(
                "invalid_request",
                "cursor pagination cannot be combined with a non-zero offset",
                details={"offset": off},
            ),
        )
    cursor_seq: int | None = None
    cursor_rid: UUID | None = None
    if use_cursor:
        try:
            cs, cr = _decode_run_list_cursor(str(cursor).strip())
            cursor_seq = cs
            cursor_rid = cr
        except (
            ValueError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
            binascii.Error,
            UnicodeDecodeError,
        ) as exc:
            raise HTTPException(
                status_code=422,
                detail=problem(
                    "invalid_cursor",
                    "cursor is not a valid keyset token",
                    details={"reason": str(exc)},
                ),
            ) from exc
    total = store.count_recent_runs(
        workflow_profile=workflow_profile,
        workflow_profile_prefix=wpfx,
        created_after=ca,
        created_before=cb,
        has_escalation=esc_filter,
        list_status=list_status_filter,
    )
    next_cursor_out: str | None = None
    if use_cursor and cursor_seq is not None and cursor_rid is not None:
        rows_page, page_has_more = store.list_recent_run_rows_cursor(
            limit=lim,
            cursor_after_seq=cursor_seq,
            cursor_after_run_id=cursor_rid,
            workflow_profile=workflow_profile,
            workflow_profile_prefix=wpfx,
            created_after=ca,
            created_before=cb,
            has_escalation=esc_filter,
            list_status=list_status_filter,
            order=order,
        )
        ids = [r[0] for r in rows_page]
        has_more = page_has_more
        off_out = 0
        if page_has_more and rows_page:
            last = rows_page[-1]
            next_cursor_out = _encode_run_list_cursor(last[1], last[0])
    else:
        ids = store.list_recent_run_ids(
            limit=lim,
            offset=off,
            workflow_profile=workflow_profile,
            workflow_profile_prefix=wpfx,
            created_after=ca,
            created_before=cb,
            has_escalation=esc_filter,
            list_status=list_status_filter,
            order=order,
        )
        has_more = off + len(ids) < total
        off_out = off
        if has_more and ids:
            mx_last = store.max_store_seq_for_run(str(ids[-1]))
            if mx_last is not None:
                next_cursor_out = _encode_run_list_cursor(mx_last, ids[-1])
    out: dict[str, Any] = {
        "run_ids": [str(x) for x in ids],
        "total": total,
        "has_more": has_more,
        "limit": lim,
        "offset": off_out,
        "order": order,
        "include_summary": include_summary,
    }
    if next_cursor_out is not None:
        out["next_cursor"] = next_cursor_out
    if workflow_profile is not None:
        out["workflow_profile"] = workflow_profile
    if wpfx is not None:
        out["workflow_profile_prefix"] = wpfx
    if created_after is not None:
        out["created_after"] = created_after
    if created_before is not None:
        out["created_before"] = created_before
    if has_escalation is not None:
        out["has_escalation"] = has_escalation
    if list_status_filter is not None:
        out["status"] = list_status_filter
    if include_summary == 1:
        summaries: dict[str, RunSummary] = {}
        for rid in ids:
            rows = store.list_run_events(str(rid))
            summaries[str(rid)] = RunSummary.model_validate(build_run_summary(rows))
        out["summaries"] = summaries
    has_more_bool = bool(out["has_more"])
    link_parts: list[str] = []
    if has_more_bool:
        if use_cursor:
            if next_cursor_out is not None:
                next_q = _runs_list_query_string(
                    limit=lim,
                    offset=None,
                    order=order,
                    include_summary=include_summary,
                    workflow_profile=workflow_profile,
                    workflow_profile_prefix=wpfx,
                    created_after=created_after,
                    created_before=created_before,
                    has_escalation=has_escalation,
                    cursor=next_cursor_out,
                    list_status=list_status_filter,
                )
                next_url = str(request.url.replace(query=next_q))
                link_parts.append(f'<{next_url}>; rel="next"')
        else:
            next_q = _runs_list_query_string(
                limit=lim,
                offset=off + len(ids),
                order=order,
                include_summary=include_summary,
                workflow_profile=workflow_profile,
                workflow_profile_prefix=wpfx,
                created_after=created_after,
                created_before=created_before,
                has_escalation=has_escalation,
                list_status=list_status_filter,
            )
            next_url = str(request.url.replace(query=next_q))
            link_parts.append(f'<{next_url}>; rel="next"')
    if not use_cursor and off > 0:
        prev_off = max(0, off - lim)
        prev_q = _runs_list_query_string(
            limit=lim,
            offset=prev_off,
            order=order,
            include_summary=include_summary,
            workflow_profile=workflow_profile,
            workflow_profile_prefix=wpfx,
            created_after=created_after,
            created_before=created_before,
            has_escalation=has_escalation,
            list_status=list_status_filter,
        )
        prev_url = str(request.url.replace(query=prev_q))
        link_parts.append(f'<{prev_url}>; rel="prev"')
    if link_parts:
        response.headers["Link"] = ", ".join(link_parts)
    return RunListResponse.model_validate(out)


@router.post(
    "/runs",
    responses={
        200: CREATE_RUN_RESPONSE_200,
        422: CREATE_RUN_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def create_run(
    body: CreateRunBody,
    orch: OrchDep,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    key_uuid: UUID | None = None
    if idempotency_key is not None and str(idempotency_key).strip():
        try:
            key_uuid = UUID(str(idempotency_key).strip())
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=problem(
                    "invalid_request",
                    "Idempotency-Key must be a UUID when set",
                    details={"header": "Idempotency-Key"},
                ),
            ) from exc
    try:
        run_id = orch.create_run(
            body.workflow_profile,
            idempotency_key=key_uuid,
            correlation_id=key_uuid,
            business_area_persona_id=body.business_area_persona_id,
            development_role_persona_id=body.development_role_persona_id,
            custom_agent_id=body.custom_agent_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("workflow_not_found", str(exc)),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("invalid_request", str(exc)),
        ) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=422,
            detail=problem("registry_key_error", str(exc)),
        ) from exc
    return {"run_id": str(run_id)}


@router.get(
    "/runs/{run_id}",
    response_model=RunDetailResponse,
    response_model_exclude_none=True,
    responses={
        200: {
            "description": "Run summary from replayed events",
            "headers": {
                "Link": RUN_DETAIL_LINK_HEADER,
            },
            "content": {
                "application/json": {
                    "example": {
                        "status": "running",
                        "workflow_profile": "default",
                        "event_count": 5,
                        "findings_count": 0,
                        "has_escalation": False,
                    },
                },
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def get_run(run_id: UUID, store: StoreDep, response: Response) -> RunDetailResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    summary = build_run_summary(rows)
    rid = str(run_id)
    response.headers["Link"] = format_run_detail_link_header(rid)
    return RunDetailResponse.model_validate({**summary, "run_id": rid})


@router.get(
    "/runs/{run_id}/timeline",
    response_model=RunTimelineResponse,
    responses={
        200: RUN_TIMELINE_RESPONSE_200,
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def timeline(run_id: UUID, store: StoreDep, response: Response) -> RunTimelineResponse:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    rid = str(run_id)
    response.headers["Link"] = format_run_timeline_link_header(rid)
    events: list[dict[str, Any]] = []
    for r in rows:
        d = serialized_event_from_row(r)
        ev = validate_event_dict(d)
        events.append(serialize_event_persistent(ev))
    ig_hist = integrator_gate_timeline_history(events)
    ig_sum = ig_hist[-1] if ig_hist else None
    ig_delta = integrator_gate_timeline_delta(events)
    re_hist = run_escalated_timeline_history(events)
    re_sum = re_hist[-1] if re_hist else None
    re_delta = run_escalated_timeline_delta(events)
    ss_hist = security_scan_on_verify_timeline_history(events)
    ss_sum = ss_hist[-1] if ss_hist else None
    sr_markers = self_refinement_marker_timeline_history(events)
    from hermes_orchestrator.micro_slice import micro_slice_timeline_summary
    from hermes_orchestrator.network_resilience_critique import (
        network_resilience_critique_timeline_summary,
    )
    from hermes_orchestrator.performance_critique import performance_critique_timeline_summary
    from hermes_orchestrator.refactor_stage import refactor_critique_timeline_summary
    from hermes_orchestrator.security_critique import security_critique_timeline_summary

    custom_agent_summary: dict[str, Any] | None = None
    for ev in events:
        if ev.get("event_type") == "run.created":
            meta = ev.get("metadata")
            if isinstance(meta, dict) and isinstance(meta.get("custom_agent"), dict):
                custom_agent_summary = meta["custom_agent"]
            break
    return RunTimelineResponse(
        run_id=rid,
        events=events,
        integrator_gate=ig_sum,
        integrator_gate_history=ig_hist or None,
        integrator_gate_delta=ig_delta,
        agent_evaluator=agent_evaluator_timeline_summary(events),
        self_refinement=self_refinement_timeline_summary(events),
        self_refinement_marker_history=sr_markers or None,
        run_escalated=re_sum,
        run_escalated_history=re_hist or None,
        run_escalated_delta=re_delta,
        security_scan_on_verify=ss_sum,
        security_scan_on_verify_history=ss_hist or None,
        preflight=preflight_timeline_summary(events),
        scraper_fetch=scraper_fetch_timeline_summary(events),
        universal_critique=universal_critique_timeline_summary(events),
        stage_graph=stage_graph_timeline_summary(events),
        parallel_writer_groups=parallel_writer_groups_timeline_summary(events),
        critic_matrix_live=critic_matrix_live_timeline_summary(events),
        persona_assignment=persona_assignment_timeline_summary(events),
        micro_slice=micro_slice_timeline_summary(events),
        custom_agent=custom_agent_summary,
        security_critique=security_critique_timeline_summary(events),
        performance_critique=performance_critique_timeline_summary(events),
        network_resilience_critique=network_resilience_critique_timeline_summary(events),
        refactor_critique=refactor_critique_timeline_summary(events),
    )


@router.get(
    "/runs/{run_id}/findings",
    responses={
        200: {
            "description": "Finding events for the run",
            "headers": {
                "Link": RUN_FINDINGS_LINK_HEADER,
            },
            "content": {
                "application/json": {
                    "example": {
                        "run_id": "11111111-1111-4111-8111-111111111111",
                        "findings": [],
                    },
                },
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def findings(run_id: UUID, store: StoreDep, response: Response) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    rid = str(run_id)
    response.headers["Link"] = format_run_findings_link_header(rid)
    out: list[dict[str, Any]] = []
    for r in rows:
        if r["event_type"] != "finding.created":
            continue
        d = serialized_event_from_row(r)
        ev = validate_event_dict(d)
        out.append(serialize_event_persistent(ev))
    return {"run_id": rid, "findings": out}


@router.post(
    "/runs/{run_id}/lifecycle/start",
    responses={
        200: {
            "description": "Preflight completed and run started",
            "content": {
                "application/json": {"example": {"status": "started"}},
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def lifecycle_start(run_id: UUID, orch: OrchDep, store: StoreDep) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    orch.start_run_after_preflight(run_id)
    return {"status": "started"}


@router.post(
    "/runs/{run_id}/lifecycle/plan",
    responses={
        200: {
            "description": "Plan stage recorded",
            "content": {
                "application/json": {"example": {"status": "plan_stage_recorded"}},
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def lifecycle_plan(run_id: UUID, orch: OrchDep, store: StoreDep) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    orch.execute_plan_stage(run_id)
    return {"status": "plan_stage_recorded"}


@router.post(
    "/runs/{run_id}/lifecycle/verify",
    responses={
        200: {
            "description": "Writer/verifier pass recorded",
            "content": {
                "application/json": {
                    "example": {"status": "verify_recorded", "dispatch": "sync"},
                },
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def lifecycle_verify(run_id: UUID, orch: OrchDep, store: StoreDep) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    repo = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    dispatch = orch.dispatch_or_run_verify(run_id, workspace=repo)
    return {"status": "verify_recorded", "dispatch": dispatch}


@router.post(
    "/runs/{run_id}/lifecycle/slice",
    responses={
        200: {
            "description": "Micro-slice pass recorded",
            "content": {
                "application/json": {
                    "example": {
                        "status": "micro_slice_recorded",
                        "slices_completed": 2,
                        "slices_blocked": 0,
                    },
                },
            },
        },
        404: PROBLEM_RESPONSE_404,
        422: PROBLEM_RESPONSE_422,
        500: PROBLEM_RESPONSE_500,
    },
)
def lifecycle_slice(run_id: UUID, orch: OrchDep, store: StoreDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    repo = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    results = orch.execute_micro_slice_pass(run_id, workspace=repo)
    completed = sum(1 for g in results if g.passed)
    blocked = len(results) - completed
    return {
        "status": "micro_slice_recorded",
        "slices_completed": completed,
        "slices_blocked": blocked,
    }
