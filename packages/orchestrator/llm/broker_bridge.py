from __future__ import annotations

from typing import Any

from broker_client.flags import broker_llm_enabled, broker_llm_only
from broker_client.stage_bind import BrokerDisabled, llm_chat_via_broker


def try_broker_chat_json(messages: list[dict], *, model: str | None = None) -> dict | None:
    """Route chat via broker when enabled.

    Mode ``1``: on failure return ``None`` (caller may fall back to Python).
    Mode ``2`` (broker-only): on failure re-raise (no Python fallback).
    """
    if not broker_llm_enabled():
        return None
    try:
        result = llm_chat_via_broker(messages, model=model)
        return result if isinstance(result, dict) else {"result": result}
    except (BrokerDisabled, RuntimeError, OSError, ValueError):
        if broker_llm_only():
            raise
        return None
