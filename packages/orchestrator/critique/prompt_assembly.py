from __future__ import annotations

from typing import Any

from agent_core.prompt_tiers import AssembledPrompt, assemble_prompt_with_cache_metadata

CRITIC_STABLE_HARNESS = (
    "You are a Nimbusware orchestration critic. Reply with JSON only. "
    "Schema matches the role-specific rubric in the session context block. "
    "Prefer PASS when evidence is healthy."
)


def assemble_critique_prompt(
    *,
    role_rubric: str,
    user_content: str,
    shared_harness: str | None = None,
) -> AssembledPrompt:
    return assemble_prompt_with_cache_metadata(
        stable=shared_harness or CRITIC_STABLE_HARNESS,
        context=role_rubric,
        volatile=user_content,
    )


def critique_messages_and_cache(
    *,
    role_rubric: str,
    user_content: str,
    shared_harness: str | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    assembled = assemble_critique_prompt(
        role_rubric=role_rubric,
        user_content=user_content,
        shared_harness=shared_harness,
    )
    return assembled.messages, assembled.cache_blocks
