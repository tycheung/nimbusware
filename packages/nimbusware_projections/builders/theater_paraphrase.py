from __future__ import annotations

import os
from typing import Any

from agent_core.models import EventType


def theater_llm_summary_enabled(rows: list[dict[str, Any]]) -> bool:
    if os.environ.get("HERMES_THEATER_LLM_SUMMARY", "").strip() == "1":
        return True
    for row in rows:
        if str(row.get("event_type") or "") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        theater = meta.get("theater")
        if isinstance(theater, dict) and theater.get("llm_summary") is True:
            return True
    return False


def apply_theater_paraphrase(
    messages: list[dict[str, Any]],
    *,
    enabled: bool,
) -> list[dict[str, Any]]:
    """Optional fo560 hook; no LLM call when disabled (default)."""
    if not enabled:
        return messages
    return messages
