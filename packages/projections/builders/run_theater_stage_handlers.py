from __future__ import annotations

from typing import Any

from projections.builders.run_theater_support import (
    SLICE_STAGE_NAMES,
    row_metadata,
    stage_name,
)
from projections.fields.theater_metadata import (
    append_agent_tool_theater_line,
    approved_research_body_md,
    path_list_summary,
)


def append_stage_started_messages(
    *,
    pl: dict[str, Any],
    row: dict[str, Any],
    base: dict[str, Any],
    messages: list[dict[str, Any]],
) -> None:
    sn = stage_name(pl)
    row_meta = row_metadata(row)
    if sn == "campaign.context.compaction.reverted":
        cid = str(row_meta.get("compaction_id") or "")
        reverted_by = str(row_meta.get("reverted_by") or "operator")
        reason = str(row_meta.get("reason") or "").strip()
        headline = (
            f"Context compaction reverted ({cid[:8]}…)"
            if len(cid) > 8
            else (f"Context compaction reverted ({cid})" if cid else "Context compaction reverted")
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
    elif sn == "run.replay.started":
        from_seq = row_meta.get("from_store_seq")
        policy = row_meta.get("replay_policy")
        compact_on = True
        if isinstance(policy, dict):
            compact_on = bool(policy.get("compact_enabled", True))
        headline = f"Replay from checkpoint (seq {from_seq})"
        body_md = f"Compaction enabled: {compact_on}"
        messages.append(
            {
                **base,
                "actor_display": "System",
                "message_kind": "context",
                "severity": "info",
                "headline": headline,
                "body_md": body_md,
                "data_testid": "theater-run-replay-started",
            },
        )
    elif sn == "interjection.drained":
        interjection = row_meta.get("interjection")
        if isinstance(interjection, dict):
            count = int(interjection.get("count") or 0)
            build = bool(interjection.get("build_from_chat"))
            headline = f"Operator interjection drained ({count} message(s))"
            if build:
                headline = f"{headline} — build-from-chat"
            interjection_lines: list[str] = []
            for msg in interjection.get("messages") or []:
                if isinstance(msg, str) and msg.strip():
                    interjection_lines.append(f"- {msg.strip()[:300]}")
            messages.append(
                {
                    **base,
                    "actor_display": "Operator",
                    "message_kind": "system",
                    "severity": "info",
                    "headline": headline,
                    "body_md": "\n".join(interjection_lines[:5]) or None,
                    "data_testid": "theater-interjection-drained",
                },
            )
    elif sn == "campaign.context.compacted":
        tokens_before = row_meta.get("tokens_before")
        tokens_after = row_meta.get("tokens_after")
        merged_count = row_meta.get("merged_handoff_count") or 0
        trigger = str(row_meta.get("compaction_trigger") or "auto")
        tb_k = f"{float(tokens_before) / 1000:.1f}k" if tokens_before else "?"
        ta_k = f"{float(tokens_after) / 1000:.1f}k" if tokens_after else "?"
        headline = f"Context compacted — {tb_k} → {ta_k} tokens ({merged_count} handoffs merged)"
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
                    "Read: " + path_list_summary({"read_files": read_files}, "read_files")
                )
            if isinstance(modified, list) and modified:
                body_parts.append(
                    "Modified: "
                    + path_list_summary({"modified_files": modified}, "modified_files"),
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
        ae = row_metadata(row).get("agent_evaluator")
        evaluation = ae.get("evaluation") if isinstance(ae, dict) else {}
        overlaps = evaluation.get("scope_overlaps") if isinstance(evaluation, dict) else None
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


def append_stage_passed_messages(
    *,
    pl: dict[str, Any],
    row: dict[str, Any],
    base: dict[str, Any],
    rows: list[dict[str, Any]],
    messages: list[dict[str, Any]],
) -> None:
    sn = stage_name(pl)
    row_meta = row_metadata(row)
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
    elif sn == "enforcement.gate":
        passed = row_meta.get("enforcement_passed")
        verdict = "PASS" if passed is not False else "FAIL"
        messages.append(
            {
                **base,
                "actor_display": "Gate",
                "message_kind": "gate",
                "severity": "pass" if verdict == "PASS" else "block",
                "headline": f"Enforcement gate {verdict} (level {row_meta.get('enforcement_level', '?')})",
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
                "body_md": approved_research_body_md(rows, plan_seq),
            },
        )
    elif sn == "interjection.build_from_chat":
        interjection = row_meta.get("interjection")
        campaign_id = ""
        if isinstance(interjection, dict):
            campaign_id = str(interjection.get("campaign_run_id") or "")
        headline = "Build-from-chat launched campaign"
        if campaign_id:
            headline = f"{headline} ({campaign_id[:8]}…)"
        messages.append(
            {
                **base,
                "actor_display": "Operator",
                "message_kind": "system",
                "severity": "info",
                "headline": headline,
                "body_md": None,
                "data_testid": "theater-interjection-build-from-chat",
            },
        )
    elif sn == "resolution.council":
        block = row_meta.get("resolution_council")
        detail = ""
        accord = False
        rounds = 0
        if isinstance(block, dict):
            detail = str(block.get("detail") or "")
            accord = bool(block.get("accord"))
            rounds = int(block.get("rounds") or 0)
        dissent = []
        if isinstance(block, dict):
            dissent_raw = block.get("dissent")
            if isinstance(dissent_raw, list):
                dissent = [str(d) for d in dissent_raw[:3] if d]
        headline = f"Resolution council: {detail or 'deliberation'}"
        if rounds:
            headline = f"{headline} ({rounds} round(s))"
        body = None
        if dissent:
            body = "Dissent: " + "; ".join(dissent)
        messages.append(
            {
                **base,
                "actor_display": "Council",
                "message_kind": "system",
                "severity": "pass" if accord else "warn",
                "headline": headline,
                "body_md": body,
                "data_testid": "theater-resolution-council",
            },
        )
    elif sn == "improvement.council":
        block = row_meta.get("improvement_council")
        selected = ""
        if isinstance(block, dict):
            selected = str(block.get("selected") or "")
        headline = "Improvement council deliberation"
        if selected:
            headline = f"{headline}: {selected.replace('_', ' ')}"
        messages.append(
            {
                **base,
                "actor_display": "Council",
                "message_kind": "system",
                "severity": "info",
                "headline": headline,
                "body_md": None,
                "data_testid": "theater-improvement-council",
            },
        )
    elif sn in SLICE_STAGE_NAMES:
        slice_id = str(row_meta.get("slice_id") or "")
        messages.append(
            {
                **base,
                "actor_display": "Slice",
                "message_kind": "slice",
                "severity": "pass",
                "headline": f"Slice stage passed: {sn}" + (f" ({slice_id})" if slice_id else ""),
                "body_md": str(row_meta.get("rationale") or "")[:400] or None,
            },
        )
        if sn == "slice.implement":
            append_agent_tool_theater_line(messages, base=base, row_meta=row_meta)


def append_stage_failed_messages(
    *,
    pl: dict[str, Any],
    row: dict[str, Any],
    base: dict[str, Any],
    messages: list[dict[str, Any]],
) -> None:
    sn = stage_name(pl)
    row_meta = row_metadata(row)
    if sn == "slice.gate":
        slice_id = str(row_meta.get("slice_id") or "")
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
    elif sn == "enforcement.gate":
        steps = row_meta.get("enforcement_steps") or []
        step_names = [str(s.get("name") if isinstance(s, dict) else s) for s in steps if s]
        detail = ", ".join(step_names[:6]) if step_names else str(pl.get("message") or "")
        messages.append(
            {
                **base,
                "actor_display": "Gate",
                "message_kind": "gate",
                "severity": "block",
                "headline": "Enforcement gate blocked (terminal CI parity)",
                "body_md": detail[:400] or None,
            },
        )
    elif sn in SLICE_STAGE_NAMES:
        slice_id = str(row_meta.get("slice_id") or "")
        messages.append(
            {
                **base,
                "actor_display": "Slice",
                "message_kind": "slice",
                "severity": "block",
                "headline": f"Slice stage failed: {sn}" + (f" ({slice_id})" if slice_id else ""),
                "body_md": str(pl.get("message") or row_meta.get("message") or "")[:500] or None,
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
