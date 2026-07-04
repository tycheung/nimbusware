from __future__ import annotations

from typing import Any


def anthropic_cache_blocks(cache_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for block in cache_blocks:
        cc = block.get("cache_control")
        if isinstance(cc, dict) and cc.get("type") == "ephemeral":
            out.append({"cache_control": cc})
    return out


def openai_prefix_reuse_enabled() -> bool:
    from env.settings_resolve import resolve_bool

    return resolve_bool("NIMBUSWARE_OPENAI_PREFIX_REUSE", default=True)


def apply_provider_cache_metadata(
    messages: list[dict[str, str]],
    *,
    provider_id: str,
    cache_blocks: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    pid = provider_id.strip().lower()
    blocks = cache_blocks or []
    if pid == "anthropic":
        return _anthropic_messages(messages, blocks)
    if pid in ("openai", "azure_openai") and openai_prefix_reuse_enabled():
        return _openai_prefix_messages(messages)
    return list(messages)


def _anthropic_messages(
    messages: list[dict[str, str]],
    cache_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not cache_blocks:
        return list(messages)
    out: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system" and anthropic_cache_blocks(cache_blocks):
            out.append(
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": content,
                            "cache_control": {"type": "ephemeral"},
                        },
                    ],
                },
            )
        else:
            out.append(dict(msg))
    return out


def _openai_prefix_messages(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
    if len(messages) < 2:
        return list(messages)
    stable_prefix = messages[0]
    return [stable_prefix, *messages[1:]]
