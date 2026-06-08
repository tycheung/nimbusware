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
    "agent_tool",
    "research",
    "stitch",
    "context",
]
Severity = Literal["info", "warn", "block", "pass"]

_SLICE_STAGE_NAMES = frozenset(
    {
        "slice.plan",
        "slice.implement",
        "slice.verify",
        "slice.critique",
        "slice.test",
        "slice.e2e",
        "slice.gate",
    },
)


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("payload")
    return dict(raw) if isinstance(raw, dict) else {}


def _stage_name(pl: dict[str, Any]) -> str:
    sn = pl.get("stage_name")
    return str(sn).strip() if isinstance(sn, str) else ""


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    raw = row.get("metadata")
    return dict(raw) if isinstance(raw, dict) else {}


def _metadata_theater_lines(row: dict[str, Any], base: dict[str, Any]) -> list[dict[str, Any]]:
    meta = _metadata(row)
    out: list[dict[str, Any]] = []
    defer = meta.get("defer_to_role")
    if isinstance(defer, dict):
        role = str(defer.get("role_id") or defer.get("role") or "role")
        reason = str(defer.get("reason_code") or defer.get("reason") or "")[:300]
        out.append(
            {
                **base,
                "actor_display": "System",
                "message_kind": "system",
                "severity": "info",
                "headline": f"Deferring to {role}",
                "body_md": reason or None,
            },
        )
    elif isinstance(defer, str) and defer.strip():
        out.append(
            {
                **base,
                "actor_display": "System",
                "message_kind": "system",
                "severity": "info",
                "headline": f"Deferring to {defer.strip()}",
                "body_md": None,
            },
        )
    creep = meta.get("scope_creep_warning")
    if isinstance(creep, str) and creep.strip():
        out.append(
            {
                **base,
                "actor_display": "System",
                "message_kind": "system",
                "severity": "warn",
                "headline": "Scope creep warning",
                "body_md": creep.strip()[:400],
            },
        )
    return out


def _governor_headline_from_run_created(meta: dict[str, Any]) -> str | None:
    gov = meta.get("resource_governor")
    if not isinstance(gov, dict):
        return None
    max_writers = gov.get("max_parallel_writers")
    tier = gov.get("hardware_tier") or gov.get("tier")
    parts: list[str] = []
    if max_writers is not None:
        parts.append(f"max parallel writers: {max_writers}")
    if tier:
        parts.append(f"tier: {tier}")
    if not parts:
        return None
    return "Resource governor — " + ", ".join(parts)


def _approved_research_body_md(rows: list[dict[str, Any]], before_seq: int) -> str | None:
    from nimbusware_projections.builders.run_research import run_research_briefs_from_events

    prior = [r for r in rows if int(r.get("store_seq") or 0) < before_seq]
    briefs = run_research_briefs_from_events(prior).get("briefs") or []
    approved = [b for b in briefs if b.get("status") == "approved"]
    if not approved:
        return None
    parts: list[str] = []
    for brief in approved:
        bid = str(brief.get("brief_id") or brief.get("artifact_id") or "").strip()
        if not bid:
            continue
        summary = str(brief.get("summary") or "").strip()[:120]
        parts.append(f"{bid} — {summary}" if summary else bid)
    if not parts:
        return None
    return "Approved research: " + "; ".join(parts)


def _append_agent_tool_theater_line(
    messages: list[dict[str, Any]],
    *,
    base: dict[str, Any],
    row_meta: dict[str, Any],
) -> None:
    raw = row_meta.get("agent_tool_log")
    if not isinstance(raw, str) or not raw.strip():
        return
    slice_id = str(row_meta.get("slice_id") or "")
    headline = "Agent tools"
    if slice_id:
        headline = f"Agent tools ({slice_id})"
    messages.append(
        {
            **base,
            "actor_display": "Agent",
            "message_kind": "agent_tool",
            "severity": "info",
            "headline": headline,
            "body_md": raw.strip()[:8000],
        },
    )


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
        messages.extend(_metadata_theater_lines(row, base))
        if et == EventType.RUN_CREATED.value:
            meta = _metadata(row)
            gov_headline = _governor_headline_from_run_created(meta)
            if gov_headline:
                messages.append(
                    {
                        **base,
                        "actor_display": "System",
                        "message_kind": "system",
                        "severity": "info",
                        "headline": gov_headline,
                        "body_md": None,
                    },
                )
        elif et == EventType.STAGE_STARTED.value:
            sn = _stage_name(pl)
            row_meta = _metadata(row)
            if sn == "campaign.context.compaction.reverted":
                cid = str(row_meta.get("compaction_id") or "")
                reverted_by = str(row_meta.get("reverted_by") or "operator")
                reason = str(row_meta.get("reason") or "").strip()
                headline = (
                    f"Context compaction reverted ({cid[:8]}…)"
                    if len(cid) > 8
                    else (
                        f"Context compaction reverted ({cid})"
                        if cid
                        else "Context compaction reverted"
                    )
                )
                revert_body = [f"Reverted by: {reverted_by}"]
                if reason:
                    revert_body.append(reason[:400])
                messages.append(
                    {
                        **base,
                        "actor_display": "System",
                        "message_kind": "context",
                        "severity": "info",
                        "headline": headline,
                        "body_md": "\n\n".join(revert_body) if revert_body else None,
                        "data_testid": "theater-context-compaction-reverted",
                    },
                )
            elif sn == "campaign.context.compacted":
                tokens_before = row_meta.get("tokens_before")
                tokens_after = row_meta.get("tokens_after")
                merged_count = row_meta.get("merged_handoff_count") or 0
                trigger = str(row_meta.get("compaction_trigger") or "auto")
                tb_k = f"{float(tokens_before) / 1000:.1f}k" if tokens_before else "?"
                ta_k = f"{float(tokens_after) / 1000:.1f}k" if tokens_after else "?"
                headline = (
                    f"Context compacted — {tb_k} → {ta_k} tokens ({merged_count} handoffs merged)"
                )
                body_parts: list[str] = []
                summary = row_meta.get("summary")
                if isinstance(summary, str) and summary.strip():
                    body_parts.append(summary.strip()[:4000])
                kept = row_meta.get("kept_event_seq_range")
                if isinstance(kept, list) and len(kept) >= 2:
                    body_parts.append(f"Kept seq range: {kept[0]}–{kept[1]}")
                if trigger:
                    body_parts.append(f"Trigger: {trigger}")
                handoff = row_meta.get("slice_handoff")
                if isinstance(handoff, dict):
                    read_files = handoff.get("read_files") or handoff.get("files_read")
                    modified = handoff.get("modified_files") or handoff.get("files_modified")
                    if isinstance(read_files, list) and read_files:
                        body_parts.append(
                            "Read: " + _path_list_summary({"read_files": read_files}, "read_files")
                        )
                    if isinstance(modified, list) and modified:
                        body_parts.append(
                            "Modified: "
                            + _path_list_summary({"modified_files": modified}, "modified_files"),
                        )
                messages.append(
                    {
                        **base,
                        "actor_display": "System",
                        "message_kind": "context",
                        "severity": "info",
                        "headline": headline,
                        "body_md": "\n\n".join(body_parts) if body_parts else None,
                        "data_testid": "theater-context-compacted",
                    },
                )
            elif sn == "slice.handoff":
                slice_id = str(row_meta.get("slice_id") or "")
                preview = str(row_meta.get("handoff_summary") or "")[:400]
                headline = f"Handoff from slice {slice_id}" if slice_id else "Slice handoff"
                messages.append(
                    {
                        **base,
                        "actor_display": "Planner",
                        "message_kind": "context",
                        "severity": "info",
                        "headline": headline,
                        "body_md": preview or None,
                        "data_testid": "theater-slice-handoff",
                    },
                )
            elif sn.startswith("agent_eval:"):
                ae = meta.get("agent_evaluator") if (meta := _metadata(row)) else {}
                evaluation = ae.get("evaluation") if isinstance(ae, dict) else {}
                overlaps = (
                    evaluation.get("scope_overlaps") if isinstance(evaluation, dict) else None
                )
                if isinstance(overlaps, list) and overlaps:
                    for warn in overlaps[:3]:
                        if isinstance(warn, str) and warn.strip():
                            messages.append(
                                {
                                    **base,
                                    "actor_display": "Agent Evaluator",
                                    "message_kind": "system",
                                    "severity": "warn",
                                    "headline": "Persona scope overlap",
                                    "body_md": warn.strip()[:400],
                                },
                            )
        elif et == EventType.MODEL_PREFLIGHT_STARTED.value:
            model = str(pl.get("requested_model_id") or "")
            messages.append(
                {
                    **base,
                    "actor_display": "System",
                    "message_kind": "system",
                    "severity": "info",
                    "headline": f"Model preflight started: {model}",
                    "body_md": str(pl.get("provider") or "")[:200] or None,
                },
            )
        elif et == EventType.MODEL_PREFLIGHT_PASSED.value:
            model = str(pl.get("validated_model_id") or "")
            latency = pl.get("p95_latency_ms")
            messages.append(
                {
                    **base,
                    "actor_display": "System",
                    "message_kind": "system",
                    "severity": "pass",
                    "headline": f"Model preflight passed: {model}",
                    "body_md": (f"p95 latency {latency}ms" if latency is not None else None),
                },
            )
        elif et == EventType.MODEL_PREFLIGHT_FAILED.value:
            model = str(pl.get("requested_model_id") or "")
            reason = str(pl.get("reason_code") or "failed")
            messages.append(
                {
                    **base,
                    "actor_display": "System",
                    "message_kind": "system",
                    "severity": "warn",
                    "headline": f"Model preflight failed: {model}",
                    "body_md": reason[:400],
                },
            )
        elif et == EventType.HARDWARE_PROFILE_DETECTED.value:
            from nimbusware_projections.builders.pressure_headline import pressure_headline

            tier = str(pl.get("hardware_tier") or pl.get("tier") or "unknown")
            level = str(pl.get("pressure_level") or "ok").strip().lower()
            severity = "info"
            if level == "warn":
                severity = "warn"
            elif level in {"throttle", "block"}:
                severity = "warn"
            headline = f"Hardware profile detected ({tier})"
            if level and level != "ok":
                headline = pressure_headline(level, pl)
            messages.append(
                {
                    **base,
                    "actor_display": "System",
                    "message_kind": "system",
                    "severity": severity,
                    "headline": headline,
                    "body_md": None,
                },
            )
        elif et == EventType.MEMORY_RETRIEVAL_EMITTED.value:
            stage = str(pl.get("stage_name") or "")
            hits = pl.get("hit_chunk_ids")
            hit_count = len(hits) if isinstance(hits, list) else 0
            messages.append(
                {
                    **base,
                    "actor_display": "System",
                    "message_kind": "system",
                    "severity": "info",
                    "headline": f"Recalled {hit_count} memory hit(s) for {stage}",
                    "body_md": None,
                },
            )
        elif et == EventType.STAGE_PASSED.value:
            sn = _stage_name(pl)
            row_meta = _metadata(row)
            if sn == "slice.gate":
                slice_id = str(row_meta.get("slice_id") or "")
                verdict = str(row_meta.get("slice_gate_verdict") or "PASS")
                messages.append(
                    {
                        **base,
                        "actor_display": "Gate",
                        "message_kind": "slice",
                        "severity": "pass" if verdict.upper() == "PASS" else "block",
                        "headline": f"Slice gate {verdict} ({slice_id or 'slice'})",
                        "body_md": None,
                    },
                )
            elif sn in ("plan", "slice.plan"):
                plan_seq = int(row.get("store_seq") or 0)
                messages.append(
                    {
                        **base,
                        "actor_display": "Planner",
                        "message_kind": "plan",
                        "severity": "pass",
                        "headline": f"Stage passed: {sn}",
                        "body_md": _approved_research_body_md(rows, plan_seq),
                    },
                )
            elif sn in _SLICE_STAGE_NAMES:
                slice_id = str(row_meta.get("slice_id") or "")
                messages.append(
                    {
                        **base,
                        "actor_display": "Slice",
                        "message_kind": "slice",
                        "severity": "pass",
                        "headline": f"Slice stage passed: {sn}"
                        + (f" ({slice_id})" if slice_id else ""),
                        "body_md": str(row_meta.get("rationale") or "")[:400] or None,
                    },
                )
                if sn == "slice.implement":
                    _append_agent_tool_theater_line(messages, base=base, row_meta=row_meta)
        elif et == EventType.STAGE_FAILED.value:
            sn = _stage_name(pl)
            row_meta = _metadata(row)
            if sn == "slice.gate":
                slice_id = str(row_meta.get("slice_id") or "")
                verdict = str(row_meta.get("slice_gate_verdict") or "FAIL")
                packet = row_meta.get("slice_context_packet")
                test_out = ""
                if isinstance(packet, dict):
                    test_out = str(packet.get("test_output") or "")[:400]
                messages.append(
                    {
                        **base,
                        "actor_display": "Gate",
                        "message_kind": "slice",
                        "severity": "block",
                        "headline": f"Slice gate blocked ({slice_id or 'slice'})",
                        "body_md": test_out or None,
                    },
                )
            elif sn in _SLICE_STAGE_NAMES:
                slice_id = str(row_meta.get("slice_id") or "")
                messages.append(
                    {
                        **base,
                        "actor_display": "Slice",
                        "message_kind": "slice",
                        "severity": "block",
                        "headline": f"Slice stage failed: {sn}"
                        + (f" ({slice_id})" if slice_id else ""),
                        "body_md": str(pl.get("message") or row_meta.get("message") or "")[:500]
                        or None,
                    },
                )
            else:
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
