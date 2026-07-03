from __future__ import annotations

SELF_REFINEMENT_SUMMARY_KEYS: tuple[str, ...] = (
    "marker_count",
    "first_marker_occurred_at",
    "last_marker_occurred_at",
    "max_iterations",
    "max_iterations_exceeded",
    "should_continue",
    "gate_decision",
    "policy_version",
    "policy_description",
)

__all__ = ["SELF_REFINEMENT_SUMMARY_KEYS"]
