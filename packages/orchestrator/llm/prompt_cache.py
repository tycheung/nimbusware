from __future__ import annotations

from typing import Any


def anthropic_cache_blocks(cache_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for block in cache_blocks:
        cc = block.get("cache_control")
        if isinstance(cc, dict) and cc.get("type") == "ephemeral":
            out.append({"cache_control": cc})
    return out


def anthropic_system_content_blocks(
    cache_blocks: list[dict[str, Any]] | None,
    *,
    fallback_system: str = "",
) -> list[dict[str, Any]] | str:
    blocks = cache_blocks or []
    segments: list[dict[str, Any]] = []
    for block in blocks:
        tier = str(block.get("tier") or "")
        if tier == "volatile":
            continue
        text = str(block.get("text") or "").strip()
        if not text:
            continue
        if block.get("cache_breaking"):
            segments.append({"type": "text", "text": text})
        elif isinstance(block.get("cache_control"), dict):
            segments.append(
                {
                    "type": "text",
                    "text": text,
                    "cache_control": block["cache_control"],
                },
            )
        else:
            segments.append({"type": "text", "text": text})
    if segments:
        return segments
    stripped = fallback_system.strip()
    return stripped if stripped else ""


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
    if pid in ("openai", "azure_openai", "openai_compatible") and openai_prefix_reuse_enabled():
        return _openai_prefix_messages(messages)
    return list(messages)


def _anthropic_messages(
    messages: list[dict[str, str]],
    cache_blocks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system = anthropic_system_content_blocks(cache_blocks, fallback_system=str(content))
            if isinstance(system, list):
                out.append({"role": "system", "content": system})
            elif system:
                out.append({"role": "system", "content": system})
            continue
        out.append(dict(msg))
    return out


def _openai_prefix_messages(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
    if len(messages) < 2:
        return list(messages)
    stable_prefix = messages[0]
    return [stable_prefix, *messages[1:]]
