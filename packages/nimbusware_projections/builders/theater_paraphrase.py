from __future__ import annotations

import os
from typing import Any

from agent_core.models import EventType


def _theater_config_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if str(row.get("event_type") or "") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        theater = meta.get("theater")
        if isinstance(theater, dict):
            return theater
    return {}


def theater_enabled(rows: list[dict[str, Any]]) -> bool:
    cfg = _theater_config_from_rows(rows)
    if cfg:
        return bool(cfg.get("enabled", True))
    return True


def theater_max_message_chars(rows: list[dict[str, Any]], *, default: int = 1200) -> int:
    cfg = _theater_config_from_rows(rows)
    raw = cfg.get("max_message_chars") if cfg else None
    if isinstance(raw, int) and raw > 0:
        return raw
    return default


def theater_llm_summary_enabled(rows: list[dict[str, Any]]) -> bool:
    if os.environ.get("NIMBUSWARE_THEATER_LLM_SUMMARY", "").strip() == "1":
        return True
    cfg = _theater_config_from_rows(rows)
    return bool(cfg.get("llm_summary")) if cfg else False


def apply_theater_paraphrase(
    messages: list[dict[str, Any]],
    *,
    enabled: bool,
) -> list[dict[str, Any]]:
    """Append a rules-based theater digest when LLM summary is enabled."""
    if not enabled or not messages:
        return messages
    kinds: dict[str, int] = {}
    for msg in messages:
        kind = str(msg.get("message_kind") or "other")
        kinds[kind] = kinds.get(kind, 0) + 1
    recent = [
        str(msg.get("headline") or "").strip()
        for msg in messages[-6:]
        if str(msg.get("headline") or "").strip()
    ]
    parts = [f"{kind}={count}" for kind, count in sorted(kinds.items())]
    body = f"Digest ({len(messages)} lines): " + ", ".join(parts)
    if recent:
        body += ". Recent: " + "; ".join(recent[:5])
    last_seq = int(messages[-1].get("store_seq") or 0)
    digest = {
        "store_seq": last_seq,
        "event_id": "",
        "occurred_at": None,
        "refs": {},
        "actor_display": "System",
        "message_kind": "summary",
        "severity": "info",
        "headline": "Theater digest",
        "body_md": body,
    }
    return [*messages, digest]
