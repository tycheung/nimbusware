from __future__ import annotations

from typing import Any, Literal

from agent_core.mapping import mapping_or_empty
from agent_core.models import EventType
from nimbusware_projections.fields.theater_metadata import (
    append_agent_tool_theater_line,
    approved_research_body_md,
    governor_headline_from_run_created,
    path_list_summary,
)

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


def _stage_name(pl: dict[str, Any]) -> str:
    sn = pl.get("stage_name")
    return str(sn).strip() if isinstance(sn, str) else ""


def _metadata(row: dict[str, Any]) -> dict[str, Any]:
    return mapping_or_empty(row.get("metadata"))


def append_theater_messages_for_row(
    et: str,
    row: dict[str, Any],
    pl: dict[str, Any],
    base: dict[str, Any],
    rows: list[dict[str, Any]],
    messages: list[dict[str, Any]],
) -> None:
    if et == EventType.RUN_CREATED.value:
        meta = _metadata(row)
        gov_headline = governor_headline_from_run_created(meta)
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
                    f"Context compaction reverted ({cid})" if cid else "Context compaction reverted"
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
            ae = meta.get("agent_evaluator") if (meta := _metadata(row)) else {}
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
        checks = list(pl.get("checks_passed") or [])
        inference_mode = None
        for token in checks:
            if isinstance(token, str) and token.startswith("inference_mode:"):
                inference_mode = token.split(":", 1)[-1].strip()
                break
        preflight_body = f"p95 latency {latency}ms" if latency is not None else None
        if inference_mode:
            from nimbusware_orchestrator.binding_preflight import _inference_mode_label

            label = _inference_mode_label(inference_mode)
            preflight_body = label if preflight_body is None else f"{label} · {preflight_body}"
        messages.append(
            {
                **base,
                "actor_display": "System",
                "message_kind": "system",
                "severity": "pass",
                "headline": f"Model preflight passed: {model}",
                "body_md": preflight_body,
            },
        )
    elif et == EventType.MODEL_BINDING_OVERRIDDEN.value:
        role = str(pl.get("agent_role") or "")
        model = str(pl.get("model_id") or "")
        provider = str(pl.get("provider_id") or "")
        messages.append(
            {
                **base,
                "actor_display": "System",
                "message_kind": "model_swap",
                "severity": "info",
                "headline": f"Model swap: {role}",
                "body_md": f"{provider} · {model}",
                "model_display": model,
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
                append_agent_tool_theater_line(messages, base=base, row_meta=row_meta)
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
        targets = path_list_summary(pl, "target_paths")
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
        files = path_list_summary(pl, "files_added")
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
