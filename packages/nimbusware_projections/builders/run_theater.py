from __future__ import annotations

from typing import Any, Literal

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from nimbusware_projections.builders.run_theater_handlers import append_theater_messages_for_row
from nimbusware_projections.fields.theater_metadata import metadata_theater_lines

MessageKind = Literal[
    "plan",
    "critic_verdict",
    "gate",
    "finding_route",
    "verifier",
    "escalation",
    "system",
    "slice",
    "agent_tool",
    "research",
    "stitch",
    "context",
]
Severity = Literal["info", "warn", "block", "pass"]


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    return mapping_or_empty(row.get("payload"))


def build_run_theater_messages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from nimbusware_projections.builders.theater_paraphrase import (
        apply_theater_paraphrase,
        theater_enabled,
        theater_llm_summary_enabled,
        theater_max_message_chars,
    )

    if not theater_enabled(rows):
        return []
    max_body = theater_max_message_chars(rows)
    messages: list[dict[str, Any]] = []
    for row in rows:
        et = str(row.get("event_type") or "")
        pl = _payload(row)
        store_seq = int(row.get("store_seq") or 0)
        base = {
            "store_seq": store_seq,
            "event_id": str(row.get("event_id") or ""),
            "occurred_at": row.get("occurred_at"),
            "refs": {"event_id": str(row.get("event_id") or "")},
        }
        messages.extend(metadata_theater_lines(row, base))
        append_theater_messages_for_row(et, row, pl, base, rows, messages)
    messages.sort(key=lambda m: int(m.get("store_seq") or 0))
    _append_why_another_round(rows, messages)
    for msg in messages:
        body = msg.get("body_md")
        if isinstance(body, str) and len(body) > max_body:
            msg["body_md"] = body[:max_body]
    from nimbusware_projections.builders.agent_tool_prune import (
        projection_prune_agent_tools_enabled,
        prune_theater_agent_tool_messages,
    )

    if projection_prune_agent_tools_enabled():
        messages = prune_theater_agent_tool_messages(messages)
    from nimbusware_orchestrator.autopilot_profiles import (
        autopilot_level_from_rows,
        autopilot_theater_filter_active,
        filter_theater_messages_for_autopilot,
    )

    if autopilot_theater_filter_active(rows):
        messages = filter_theater_messages_for_autopilot(
            messages,
            level=autopilot_level_from_rows(rows),
        )
    return apply_theater_paraphrase(
        messages,
        enabled=theater_llm_summary_enabled(rows),
    )


def _append_why_another_round(rows: list[dict[str, Any]], messages: list[dict[str, Any]]) -> None:
    failing_critics: list[str] = []
    categories: list[str] = []
    last_gate_fail_seq = 0
    for row in rows:
        et = str(row.get("event_type") or "")
        pl = _payload(row)
        if et == EventType.CRITIC_VERDICT_EMITTED.value and str(pl.get("verdict")) != "PASS":
            failing_critics.append(str(pl.get("critic_role") or "Critic"))
        if et == EventType.FINDING_ROUTED.value:
            cat = pl.get("category")
            if isinstance(cat, str) and cat.strip():
                categories.append(cat.strip())
        if et == EventType.GATE_DECISION_EMITTED.value and str(pl.get("verdict")) != "PASS":
            last_gate_fail_seq = int(row.get("store_seq") or 0)
    if not failing_critics and last_gate_fail_seq == 0:
        return
    critics_txt = ", ".join(dict.fromkeys(failing_critics)) or "gate"
    cats_txt = ", ".join(dict.fromkeys(categories)) or "see findings"
    messages.append(
        {
            "store_seq": last_gate_fail_seq or (messages[-1]["store_seq"] if messages else 0),
            "event_id": "",
            "occurred_at": None,
            "refs": {},
            "actor_display": "System",
            "message_kind": "gate",
            "severity": "warn",
            "headline": "Why another round?",
            "body_md": (
                f"Blocking: {critics_txt}. Categories: {cats_txt}. "
                "Review routed findings and retry or approve overrides in Admin."
            ),
        },
    )
    messages.sort(key=lambda m: int(m.get("store_seq") or 0))
