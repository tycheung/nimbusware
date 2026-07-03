from __future__ import annotations

AGENT_EVALUATOR_SUMMARY_KEYS: tuple[str, ...] = (
    "stage_name",
    "score",
    "score_band",
    "verdict",
    "persona_id",
    "auto_promote_requested",
    "auto_promote_applied",
    "auto_create_requested",
    "auto_create_applied",
)

__all__ = ["AGENT_EVALUATOR_SUMMARY_KEYS"]
