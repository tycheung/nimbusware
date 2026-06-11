from __future__ import annotations

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType

INTERJECTION_ENQUEUED_STAGE = "interjection.enqueued"
INTERJECTION_DRAINED_STAGE = "interjection.drained"
SLICE_PLAN_STAGE = "slice.plan"
DEFAULT_SLO_SLICE_CYCLES = 1


def _stage_name(row: dict) -> str:
    return str(mapping_or_empty(row.get("payload")).get("stage_name") or "")


def _occurred_at(row: dict) -> str:
    return str(row.get("occurred_at") or "")


def _is_stage_started(row: dict) -> bool:
    et = str(row.get("event_type") or "")
    return et in {EventType.STAGE_STARTED.value, "stage.started"}


def interjection_slo_summary(
    events: list[dict],
    *,
    pending_queue_count: int = 0,
) -> dict:
    enqueues: list[dict] = []
    drains: list[dict] = []
    slice_plan_starts: list[str] = []
    for row in events:
        sn = _stage_name(row)
        if sn == INTERJECTION_ENQUEUED_STAGE:
            meta = mapping_or_empty(mapping_or_empty(row.get("metadata")).get("interjection"))
            enqueues.append(
                {
                    "occurred_at": _occurred_at(row),
                    "message": str(meta.get("message") or "")[:200],
                    "priority": str(meta.get("priority") or "next"),
                },
            )
        elif sn == INTERJECTION_DRAINED_STAGE and _is_stage_started(row):
            meta = mapping_or_empty(mapping_or_empty(row.get("metadata")).get("interjection"))
            drains.append(
                {
                    "occurred_at": _occurred_at(row),
                    "count": int(meta.get("count") or 0),
                },
            )
        elif sn == SLICE_PLAN_STAGE and _is_stage_started(row):
            slice_plan_starts.append(_occurred_at(row))

    overdue: list[dict] = []
    for eq in enqueues:
        eq_at = eq["occurred_at"]
        next_plan = next((t for t in slice_plan_starts if t > eq_at), None)
        drained_before_plan = any(
            d["occurred_at"] > eq_at and (next_plan is None or d["occurred_at"] < next_plan)
            for d in drains
        )
        if next_plan and not drained_before_plan:
            overdue.append({**eq, "next_slice_plan_at": next_plan})

    return {
        "slo_target_slice_cycles": DEFAULT_SLO_SLICE_CYCLES,
        "enqueued_count": len(enqueues),
        "drained_count": len(drains),
        "overdue_count": len(overdue) + (1 if pending_queue_count > 0 else 0),
        "overdue_items": overdue,
        "pending_queue_count": pending_queue_count,
        "slo_met": len(overdue) == 0 and pending_queue_count == 0,
    }


def interjection_slo_markdown(
    summary: dict,
    *,
    pending_queue_count: int = 0,
) -> str:
    slo_cycles = int(summary.get("slo_target_slice_cycles") or DEFAULT_SLO_SLICE_CYCLES)
    lines = [
        f"**Interjection SLO:** drain within **{slo_cycles}** slice cycle(s) of enqueue.",
        f"- Enqueued: **{summary.get('enqueued_count', 0)}**",
        f"- Drained: **{summary.get('drained_count', 0)}**",
    ]
    pending = int(summary.get("pending_queue_count") or pending_queue_count)
    if pending:
        lines.append(f"- **Pending queue:** {pending} message(s) (live)")
    overdue = int(summary.get("overdue_count") or 0)
    if overdue:
        lines.append(f"- **SLO breach:** {overdue} overdue interjection(s)")
        for item in summary.get("overdue_items") or []:
            msg = str(item.get("message") or "").strip()
            snippet = f' — "{msg[:80]}"' if msg else ""
            lines.append(f"  - {item.get('occurred_at', '—')}{snippet}")
    elif summary.get("slo_met"):
        lines.append("- Status: **within SLO**")
    elif summary.get("enqueued_count", 0) == 0 and pending == 0:
        lines.append("- No interjection events on this run.")
    return "\n".join(lines)
