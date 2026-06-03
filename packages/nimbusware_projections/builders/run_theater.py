from __future__ import annotations

from typing import Any, Literal

from agent_core.models import EventType

MessageKind = Literal[
    "plan",
    "critic_verdict",
    "gate",
    "finding_route",
    "verifier",
    "escalation",
    "system",
    "slice",
    "research",
    "stitch",
]
Severity = Literal["info", "warn", "block", "pass"]


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("payload")
    return dict(raw) if isinstance(raw, dict) else {}


def _stage_name(pl: dict[str, Any]) -> str:
    sn = pl.get("stage_name")
    return str(sn).strip() if isinstance(sn, str) else ""


def build_run_theater_messages(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
        if et == EventType.STAGE_PASSED.value:
            sn = _stage_name(pl)
            if sn in ("plan", "slice.plan"):
                messages.append(
                    {
                        **base,
                        "actor_display": "Planner",
                        "message_kind": "plan",
                        "severity": "pass",
                        "headline": f"Stage passed: {sn}",
                        "body_md": None,
                    },
                )
            elif sn.startswith("slice."):
                messages.append(
                    {
                        **base,
                        "actor_display": "Slice",
                        "message_kind": "slice",
                        "severity": "pass",
                        "headline": f"Slice stage passed: {sn}",
                        "body_md": None,
                    },
                )
        elif et == EventType.STAGE_FAILED.value:
            sn = _stage_name(pl)
            messages.append(
                {
                    **base,
                    "actor_display": "Verifier",
                    "message_kind": "verifier",
                    "severity": "block",
                    "headline": f"Stage failed: {sn}",
                    "body_md": str(pl.get("message") or "")[:500] or None,
                },
            )
        elif et == EventType.CRITIC_VERDICT_EMITTED.value:
            verdict = str(pl.get("verdict") or "UNKNOWN")
            critic = str(pl.get("critic_template") or "Critic")
            sev: Severity = "pass" if verdict == "PASS" else "block"
            messages.append(
                {
                    **base,
                    "actor_display": critic,
                    "message_kind": "critic_verdict",
                    "severity": sev,
                    "headline": f"{critic}: {verdict}",
                    "body_md": str(pl.get("rationale") or "")[:800] or None,
                },
            )
        elif et == EventType.GATE_DECISION_EMITTED.value:
            decision = str(pl.get("decision") or "")
            sev_gate: Severity = "pass" if decision == "PASS" else "block"
            messages.append(
                {
                    **base,
                    "actor_display": "Gate",
                    "message_kind": "gate",
                    "severity": sev_gate,
                    "headline": f"Gate {decision}",
                    "body_md": str(pl.get("reason_code") or "")[:400] or None,
                },
            )
        elif et == EventType.FINDING_ROUTED.value:
            messages.append(
                {
                    **base,
                    "actor_display": "Router",
                    "message_kind": "finding_route",
                    "severity": "info",
                    "headline": "Finding routed",
                    "body_md": str(pl.get("category") or "")[:200] or None,
                },
            )
        elif et == EventType.RUN_ESCALATED.value:
            messages.append(
                {
                    **base,
                    "actor_display": "System",
                    "message_kind": "escalation",
                    "severity": "warn",
                    "headline": "Run escalated",
                    "body_md": str(pl.get("notes") or pl.get("reason_code") or "")[:400] or None,
                },
            )
        elif et == EventType.RESEARCH_BRIEF_EMITTED.value:
            kind = str(pl.get("brief_kind") or "research")
            messages.append(
                {
                    **base,
                    "actor_display": "Researcher",
                    "message_kind": "research",
                    "severity": "info",
                    "headline": f"{kind} brief: {pl.get('domain_tag', '')}",
                    "body_md": str(pl.get("summary") or "")[:600] or None,
                },
            )
        elif et in (EventType.STITCH_APPLIED.value, EventType.STITCH_PLAN_EMITTED.value):
            messages.append(
                {
                    **base,
                    "actor_display": "Stitcher",
                    "message_kind": "stitch",
                    "severity": "info",
                    "headline": "Stitch update",
                    "body_md": None,
                },
            )
    messages.sort(key=lambda m: int(m.get("store_seq") or 0))
    return messages
