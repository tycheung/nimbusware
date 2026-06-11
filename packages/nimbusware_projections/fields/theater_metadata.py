from __future__ import annotations

from typing import Any

from agent_core.mapping import mapping_or_empty


def metadata_theater_lines(row: dict[str, Any], base: dict[str, Any]) -> list[dict[str, Any]]:
    meta = mapping_or_empty(row.get("metadata"))
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


def governor_headline_from_run_created(meta: dict[str, Any]) -> str | None:
    from agent_core.mapping import mapping_or_empty

    gov = mapping_or_empty(meta.get("resource_governor"))
    if not gov:
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


def approved_research_body_md(rows: list[dict[str, Any]], before_seq: int) -> str | None:
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


def append_agent_tool_theater_line(
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


def path_list_summary(pl: dict[str, Any], key: str, *, max_items: int = 3) -> str:
    raw = pl.get(key)
    if not isinstance(raw, list) or not raw:
        return ""
    parts = [str(p).strip() for p in raw if str(p).strip()][:max_items]
    if not parts:
        return ""
    suffix = f" (+{len(raw) - len(parts)} more)" if len(raw) > len(parts) else ""
    return ", ".join(parts) + suffix
