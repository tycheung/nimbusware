from __future__ import annotations

from typing import Any

from agent_core.context_budget import estimate_tokens, truncate_for_llm_history
from agent_core.mapping import mapping_or_empty


def agent_compact_mode() -> str:
    from env.settings_resolve import resolve_str

    raw = resolve_str("NIMBUSWARE_AGENT_COMPACT", default="1").strip().lower()
    if raw in ("0", "false", "off", "no"):
        return "off"
    if raw == "full":
        return "full"
    return "handoff"


def agent_context_window_tokens(default: int = 32000) -> int:
    from env.env_flags import nimbusware_agent_context_window_tokens

    return nimbusware_agent_context_window_tokens(default=default)


def maybe_full_compact_messages(
    messages: list[dict[str, str]],
    *,
    preserve_prefix: int = 2,
) -> tuple[list[dict[str, str]], int]:
    """L4: summarize middle turns when estimated tokens exceed ~90% of role window."""
    if agent_compact_mode() != "full":
        return messages, 0
    window = agent_context_window_tokens()
    threshold = int(window * 0.9)
    total = sum(estimate_tokens(str(m.get("content") or "")) for m in messages)
    if total <= threshold or len(messages) <= preserve_prefix + 2:
        return messages, 0

    head = messages[:preserve_prefix]
    tail = messages[-2:]
    middle = messages[preserve_prefix:-2]
    if not middle:
        return messages, 0

    sections: list[str] = []
    for msg in middle:
        role = str(msg.get("role") or "user")
        content = str(msg.get("content") or "").strip()
        if not content:
            continue
        if role == "user" and content.startswith("Operator steer"):
            sections.append(content)
            continue
        preview = truncate_for_llm_history(content, max_chars=400)
        sections.append(f"[{role}] {preview}")

    summary = (
        "## Compacted prior turns\n"
        + "\n".join(sections[:40])
        + f"\n\n(compacted {len(middle)} messages; saved ~{total - threshold} est. tokens)"
    )
    compacted = [
        *head,
        {"role": "user", "content": summary},
        *tail,
    ]
    after = sum(estimate_tokens(str(m.get("content") or "")) for m in compacted)
    return compacted, max(0, total - after)


def handoff_compact_budget_exceeded(
    events: list[dict[str, Any]],
    *,
    keep_recent_tokens: int | None = None,
) -> bool:
    from orchestrator.context_compaction import _handoff_events
    from env.env_flags import nimbusware_campaign_keep_recent_tokens

    handoffs = _handoff_events(events)
    if len(handoffs) < 2:
        return False
    keep = keep_recent_tokens
    if keep is None:
        keep = nimbusware_campaign_keep_recent_tokens()
    total = sum(
        estimate_tokens(str(mapping_or_empty(r.get("metadata")).get("handoff_summary") or ""))
        for r in handoffs
    )
    return total > keep
