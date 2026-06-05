"""Stable / context / volatile prompt assembly for cache-friendly LLM calls."""

from __future__ import annotations

from enum import Enum


class PromptTier(str, Enum):
    STABLE = "stable"
    CONTEXT = "context"
    VOLATILE = "volatile"


def assemble_prompt(
    *,
    stable: str,
    context: str = "",
    volatile: str = "",
) -> list[dict[str, str]]:
    """Build chat messages with stable system block and split user tiers."""
    system_parts = [stable.strip()]
    if context.strip():
        system_parts.append(context.strip())
    user_parts = [volatile.strip()] if volatile.strip() else []
    messages: list[dict[str, str]] = [
        {"role": "system", "content": "\n\n".join(system_parts)},
    ]
    if user_parts:
        messages.append({"role": "user", "content": user_parts[0]})
    return messages


def stable_slice_agent_block(*, tool_rules: str) -> str:
    return (
        "You are a Nimbusware slice agent.\n"
        f"{tool_rules.strip()}\n"
        "Reply with JSON only. Do not include timestamps in your reasoning."
    )
