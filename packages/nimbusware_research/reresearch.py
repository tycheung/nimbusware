"""Bounded re-research when plan stage fails for missing context."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from agent_core.models import EventType
from nimbusware_store.protocol import EventStore


def reresearch_enabled() -> bool:
    from nimbusware_env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_RERESARCH_MISSING_CONTEXT", default=False)


def plan_failure_needs_reresearch(rows: list[dict[str, Any]]) -> bool:
    for row in reversed(rows):
        if row.get("event_type") != EventType.STAGE_FAILED.value:
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if payload.get("stage_name") not in ("plan", "planner.critique"):
            continue
        reason = str(payload.get("reason_code", "")).lower()
        msg = str(payload.get("message", "")).lower()
        if "missing_context" in reason or "missing_context" in msg:
            return True
        if reason == "planner_critique_gate_fail":
            return True
    return False


def research_brief_count(rows: list[dict[str, Any]]) -> int:
    return sum(1 for r in rows if r.get("event_type") == EventType.RESEARCH_BRIEF_EMITTED.value)


def maybe_reresearch_after_plan_fail(
    store: EventStore,
    *,
    run_id: UUID,
    repo_root: Any,
    registry: Any,
    critique_router: Any,
    requirements: dict[str, Any] | None,
    research_meta: dict[str, Any],
    max_rounds: int = 2,
) -> bool:
    """Re-run research stages once when plan failed for missing context."""
    if not reresearch_enabled():
        return False
    rows = store.list_run_events(str(run_id))
    if not plan_failure_needs_reresearch(rows):
        return False
    if research_brief_count(rows) >= max_rounds * 2:
        return False
    from nimbusware_research.stages import emit_research_stages_stub

    emit_research_stages_stub(
        store,
        registry,
        critique_router,
        run_id=run_id,
        repo_root=repo_root,
        requirements=requirements,
        research_meta=research_meta,
    )
    return True
