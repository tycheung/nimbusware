"""Integrator gate timeline builders — shared by API and console."""

from __future__ import annotations

from typing import Any

from agent_core.models import EventType
from nimbusware_projections.fields.integrator_gate import INTEGRATOR_GATE_ROW_KEYS


def integrator_gate_row_from_event(ev: dict[str, Any]) -> dict[str, Any]:
    """Shape one timeline row from a ``gate.decision.emitted`` event (caller filters type)."""
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
        hist.append(integrator_gate_row_from_event(ev))
    return hist


def integrator_gate_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest integrator gate decision."""
    hist = integrator_gate_timeline_entries(events)
    return hist[-1] if hist else None


def integrator_gate_timeline_history(
    events: list[dict[str, Any]],
    *,
    limit: int = 25,
) -> list[dict[str, Any]]:
    """Bounded integrator gate history (latest entries win when trimmed)."""
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
    """Latest integrator gate vs the immediately prior gate."""
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


__all__ = [
    "INTEGRATOR_GATE_ROW_KEYS",
    "integrator_gate_row_from_event",
    "integrator_gate_timeline_delta",
    "integrator_gate_timeline_entries",
    "integrator_gate_timeline_history",
    "integrator_gate_timeline_summary",
]
