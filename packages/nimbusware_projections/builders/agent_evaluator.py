from __future__ import annotations

from typing import Any

from agent_core.models import EventType
from hermes_extensions.phase2 import agent_evaluator_score_band
from nimbusware_projections.fields.agent_evaluator import AGENT_EVALUATOR_SUMMARY_KEYS

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


__all__ = [
    "AGENT_EVALUATOR_SUMMARY_KEYS",
    "agent_evaluator_timeline_summary",
]
