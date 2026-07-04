from __future__ import annotations

from typing import Any


def record_provider_chat_telemetry(
    raw: dict[str, Any],
    *,
    provider: str,
    stage_name: str = "",
) -> None:
    if not isinstance(raw, dict):
        return
    from agent_core.token_telemetry import (
        TokenTelemetrySample,
        record_token_sample,
        usage_from_provider_response,
    )

    usage = usage_from_provider_response(raw)
    record_token_sample(
        TokenTelemetrySample(
            tokens_in=usage.get("tokens_in", 0),
            tokens_out=usage.get("tokens_out", 0),
            cache_read=usage.get("cache_read", 0),
            cache_write=usage.get("cache_write", 0),
            provider=provider,
            stage_name=stage_name,
        ),
    )
