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


def _path_list_summary(pl: dict[str, Any], key: str, *, max_items: int = 3) -> str:
    raw = pl.get(key)
    if not isinstance(raw, list) or not raw:
        return ""
    parts = [str(p).strip() for p in raw if str(p).strip()][:max_items]
    if not parts:
        return ""
    suffix = f" (+{len(raw) - len(parts)} more)" if len(raw) > len(parts) else ""
    return ", ".join(parts) + suffix


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
            critic = str(pl.get("critic_role") or pl.get("critic_template") or "Critic")
            sev: Severity = "pass" if verdict == "PASS" else "block"
            messages.append(
                {
                    **base,
                    "actor_display": critic,
                    "message_kind": "critic_verdict",
                    "severity": sev,
                    "headline": f"{critic}: {verdict}",
                    "body_md": None,
                },
            )
        elif et == EventType.GATE_DECISION_EMITTED.value:
            verdict_gate = str(pl.get("verdict") or "")
            sev_gate: Severity = "pass" if verdict_gate == "PASS" else "block"
            messages.append(
                {
                    **base,
                    "actor_display": "Gate",
                    "message_kind": "gate",
                    "severity": sev_gate,
                    "headline": f"Gate {verdict_gate} ({pl.get('stage_name', '')})",
                    "body_md": str(pl.get("failure_reason_code") or "")[:400] or None,
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
        elif et == EventType.RESEARCH_PATTERN_INDEXED.value:
            pattern_id = str(pl.get("pattern_id") or "")
            repo_url = str(pl.get("repo_url") or "")[:200]
            messages.append(
                {
                    **base,
                    "actor_display": "Researcher",
                    "message_kind": "research",
                    "severity": "info",
                    "headline": f"Pattern indexed: {pattern_id}",
                    "body_md": repo_url or None,
                },
            )
        elif et == EventType.DOMAIN_CRITIC_PROPOSED.value:
            template = str(pl.get("critic_template") or "critic")
            messages.append(
                {
                    **base,
                    "actor_display": "Researcher",
                    "message_kind": "research",
                    "severity": "info",
                    "headline": f"Domain critic proposed: {template}",
                    "body_md": str(pl.get("blocking_authority") or "")[:200] or None,
                },
            )
        elif et == "transplant.candidate.selected":
            source_kind = str(pl.get("source_kind") or "unknown")
            candidate_id = str(pl.get("candidate_id") or "")[:80]
            messages.append(
                {
                    **base,
                    "actor_display": "Stitcher",
                    "message_kind": "stitch",
                    "severity": "info",
                    "headline": f"Transplant candidate selected ({source_kind})",
                    "body_md": candidate_id or None,
                },
            )
        elif et == EventType.STITCH_PLAN_EMITTED.value:
            targets = _path_list_summary(pl, "target_paths")
            headline = f"Stitch plan: {targets}" if targets else "Stitch plan emitted"
            messages.append(
                {
                    **base,
                    "actor_display": "Stitcher",
                    "message_kind": "stitch",
                    "severity": "info",
                    "headline": headline,
                    "body_md": str(pl.get("wiring_delta_summary") or "")[:600] or None,
                },
            )
        elif et == EventType.STITCH_APPLIED.value:
            files = _path_list_summary(pl, "files_added")
            headline = f"Stitch applied: {files}" if files else "Stitch applied"
            messages.append(
                {
                    **base,
                    "actor_display": "Stitcher",
                    "message_kind": "stitch",
                    "severity": "info",
                    "headline": headline,
                    "body_md": str(pl.get("snapshot_ref") or "")[:200] or None,
                },
            )
        elif et == EventType.STITCH_FAILED.value:
            reason = str(pl.get("reason_code") or "failed")
            messages.append(
                {
                    **base,
                    "actor_display": "Stitcher",
                    "message_kind": "stitch",
                    "severity": "block",
                    "headline": f"Stitch failed: {reason}",
                    "body_md": str(pl.get("rollback_snapshot_ref") or "")[:200] or None,
                },
            )
    messages.sort(key=lambda m: int(m.get("store_seq") or 0))
    _append_why_another_round(rows, messages)
    return messages


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
