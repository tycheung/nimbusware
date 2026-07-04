from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PromptTier(str, Enum):
    STABLE = "stable"
    CONTEXT = "context"
    VOLATILE = "volatile"
    DYNAMIC = "dynamic"


@dataclass(frozen=True)
class CacheBreakingSection:
    """Marks content that must not participate in provider prompt-cache reuse."""

    label: str
    content: str
    cache_breaking: bool = True


@dataclass
class AssembledPrompt:
    messages: list[dict[str, str]]
    cache_blocks: list[dict[str, Any]] = field(default_factory=list)


def assemble_prompt(
    *,
    stable: str,
    context: str = "",
    volatile: str = "",
) -> list[dict[str, str]]:
    return assemble_prompt_with_cache_metadata(
        stable=stable,
        context=context,
        volatile=volatile,
    ).messages


def assemble_prompt_with_cache_metadata(
    *,
    stable: str,
    context: str = "",
    volatile: str = "",
    dynamic_sections: list[CacheBreakingSection] | None = None,
) -> AssembledPrompt:
    system_parts: list[str] = [stable.strip()]
    cache_blocks: list[dict[str, Any]] = [
        {"tier": PromptTier.STABLE.value, "cache_control": {"type": "ephemeral"}},
    ]
    if context.strip():
        system_parts.append(context.strip())
        cache_blocks.append(
            {"tier": PromptTier.CONTEXT.value, "cache_control": {"type": "ephemeral"}},
        )
    for section in dynamic_sections or []:
        if not section.content.strip():
            continue
        system_parts.append(section.content.strip())
        cache_blocks.append(
            {
                "tier": PromptTier.DYNAMIC.value,
                "label": section.label,
                "cache_breaking": section.cache_breaking,
            },
        )
        if section.cache_breaking:
            logger.debug("cache-breaking prompt section changed: %s", section.label)
    user_parts = [volatile.strip()] if volatile.strip() else []
    messages: list[dict[str, str]] = [
        {"role": "system", "content": "\n\n".join(system_parts)},
    ]
    if user_parts:
        messages.append({"role": "user", "content": user_parts[0]})
        cache_blocks.append({"tier": PromptTier.VOLATILE.value, "cache_breaking": True})
    return AssembledPrompt(messages=messages, cache_blocks=cache_blocks)


def stable_slice_agent_block(*, tool_rules: str) -> str:
    return (
        "You are a Nimbusware slice agent.\n"
        f"{tool_rules.strip()}\n"
        "Reply with JSON only. Do not include timestamps in your reasoning."
    )
