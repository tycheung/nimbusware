from __future__ import annotations

from datetime import datetime
from typing import Any

from nimbusware_console.explainer_core.display_common import (
    stringify_display_value as _stringify,  # noqa: F401
)

__all__ = ("_parse_iso_utc", "_stringify")

_SELF_REFINEMENT_FIELDS: tuple[tuple[str, str], ...] = (
    ("version", "Version"),
    ("description", "Description"),
    ("stage_name", "Stage name"),
    ("attempt", "Attempt"),
    ("gate_decision", "Gate decision"),
    ("loops_remaining", "Loops remaining"),
    ("ungated_loop", "Ungated loop"),
    ("ungated_iteration_count", "Ungated iteration count"),
    ("iteration_progress_ratio", "Iteration progress ratio"),
    ("should_continue", "Should continue"),
    ("orchestration_branch", "Orchestration branch"),
    ("max_iterations", "Max iterations"),
    ("max_iterations_exceeded", "Max iterations exceeded"),
    ("auto_promote_requested", "Auto-promote requested"),
    ("auto_promote_applied", "Auto-promote applied"),
    ("auto_promote_reason", "Auto-promote reason"),
    ("prior_gate_verdict", "Prior gate verdict"),
    ("phase_d_signal", "Phase D loop signal"),
    ("llm_critique_stage", "LLM critique panel gate"),
    ("llm_critique_summary", "LLM critique summary"),
    ("evaluation_status", "Evaluation status"),
    ("evaluation_gaps", "Evaluation gaps"),
    ("promotion_ready", "Promotion ready"),
    ("coverage_business_area_id", "Coverage business area id"),
    ("coverage_development_role_id", "Coverage development role id"),
    ("marker_count", "Marker count (session)"),
    ("first_marker_occurred_at", "First marker occurred at"),
    ("last_marker_occurred_at", "Last marker occurred at"),
    ("event_id", "Event id"),
    ("occurred_at", "Occurred at"),
)


def _parse_iso_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None
