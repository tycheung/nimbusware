from __future__ import annotations

from typing import Any

from agent_core.models import EventType


def research_summary_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    domain_briefs: list[dict[str, Any]] = []
    code_briefs: list[dict[str, Any]] = []
    patterns: list[dict[str, Any]] = []
    critic_proposals: list[dict[str, Any]] = []
    for row in events:
        et = str(row.get("event_type") or "")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        if et == EventType.RESEARCH_BRIEF_EMITTED.value:
            kind = str(payload.get("brief_kind") or "")
            if kind == "domain":
                domain_briefs.append(payload)
            elif kind == "code":
                code_briefs.append(payload)
        elif et == EventType.RESEARCH_PATTERN_INDEXED.value:
            patterns.append(payload)
        elif et == EventType.DOMAIN_CRITIC_PROPOSED.value:
            critic_proposals.append(payload)
    return {
        "domain_briefs": domain_briefs,
        "code_briefs": code_briefs,
        "patterns": patterns,
        "domain_critic_proposals": critic_proposals,
    }
