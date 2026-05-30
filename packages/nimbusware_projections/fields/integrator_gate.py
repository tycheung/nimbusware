"""Integrator gate field metadata — shared by API and console."""

from __future__ import annotations

INTEGRATOR_GATE_ROW_KEYS: tuple[str, ...] = (
    "event_id",
    "occurred_at",
    "stage_name",
    "verdict",
    "failure_reason_code",
    "bundle_id",
    "bundle_title",
    "integrator_score",
    "min_score_to_pass",
    "integrator_project_tags",
    "integrator_bundle_tags",
    "integrator_matched_tags",
    "bundle_compatibility_ranking",
    "bundle_compatibility_ranking_count",
    "selected_bundle_rank",
    "selected_bundle_id",
)

INTEGRATOR_GATE_DISPLAY_FIELDS: tuple[tuple[str, str], ...] = (
    ("verdict", "Verdict"),
    ("failure_reason_code", "Failure reason code"),
    ("stage_name", "Stage name"),
    ("bundle_id", "Bundle id"),
    ("bundle_title", "Bundle title"),
    ("integrator_score", "Integrator score"),
    ("min_score_to_pass", "Min score to pass"),
    ("integrator_project_tags", "Project tags"),
    ("integrator_bundle_tags", "Bundle tags"),
    ("integrator_matched_tags", "Matched tags"),
    ("event_id", "Event id"),
    ("occurred_at", "Occurred at"),
)

__all__ = ["INTEGRATOR_GATE_DISPLAY_FIELDS", "INTEGRATOR_GATE_ROW_KEYS"]
