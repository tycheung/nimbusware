from __future__ import annotations

from typing import Any

from agent_core.models import EventType
from projections.builders.run_theater_stage_handlers import (
    append_stage_failed_messages,
    append_stage_passed_messages,
    append_stage_started_messages,
)
from projections.builders.run_theater_support import (
    Severity,
    row_metadata,
)
from projections.fields.theater_metadata import (
    governor_headline_from_run_created,
    path_list_summary,
)


def append_theater_messages_for_row(
    et: str,
    row: dict[str, Any],
    pl: dict[str, Any],
    base: dict[str, Any],
    rows: list[dict[str, Any]],
    messages: list[dict[str, Any]],
) -> None:
    if et == EventType.RUN_CREATED.value:
        meta = row_metadata(row)
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
        append_stage_started_messages(pl=pl, row=row, base=base, messages=messages)
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
            from orchestrator.routing.preflight import _inference_mode_label

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
        from projections.builders.pressure_headline import pressure_headline

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
        append_stage_passed_messages(pl=pl, row=row, base=base, rows=rows, messages=messages)
    elif et == EventType.STAGE_FAILED.value:
        append_stage_failed_messages(pl=pl, row=row, base=base, messages=messages)
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
