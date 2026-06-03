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
    if os.environ.get("HERMES_THEATER_LLM_SUMMARY", "").strip() == "1":
        return True
    cfg = _theater_config_from_rows(rows)
    return bool(cfg.get("llm_summary")) if cfg else False


def apply_theater_paraphrase(
    messages: list[dict[str, Any]],
    *,
    enabled: bool,
) -> list[dict[str, Any]]:
    """Optional fo560 hook; no LLM call when disabled (default)."""
    if not enabled:
        return messages
    return messages
