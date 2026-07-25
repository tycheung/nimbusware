"""SSE stream peel envelopes (`sak489-f` / `sak490-f` / `sak496-g`).

Emit standard ``event: error`` bodies ``{via, feature, error, status}`` before closing
streams when COMPUTE or LLM peel blocks local streaming.
"""

from __future__ import annotations

import json
from typing import Any

from broker_client.dual_run_route import refuse_broker_only_http as _refuse_broker_only_http
from broker_client.flags import (
    broker_compute_enabled,
    broker_compute_only,
    broker_llm_enabled,
    broker_llm_only,
)
from broker_client.peel_assert import build_http_miss
from compute.broker_route import COMPUTE_ONLY_MSG

LLM_ONLY_MSG = (
    "Nimbusware chat stream unavailable under "
    "NIMBUSWARE_BROKER_LLM=2; use SwissArmyNoife llm_chat"
)


def sse_pack(event: str, data: dict[str, Any]) -> str:
    """Format one SSE frame."""
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def sse_peel_miss_body(*, feature: str, error: str) -> dict[str, Any]:
    """Standard peel miss payload for SSE ``event: error``."""
    return build_http_miss(error, feature=feature, status="degraded")


def sse_error_envelope(
    *,
    feature: str,
    error: str,
    via: str = "broker_miss",
    status: str = "degraded",
) -> str:
    """One ``event: error`` frame with standard peel fields."""
    return sse_pack(
        "error",
        {
            "via": via,
            "feature": feature,
            "error": error,
            "status": status,
        },
    )


def early_sse_peel_miss(*, feature: str, error: str | None = None) -> str | None:
    if not broker_compute_enabled():
        return None
    msg = error or (
        f"{feature} stream unavailable under NIMBUSWARE_BROKER_COMPUTE peel; "
        "broker stream path required"
    )
    _refuse_broker_only_http(
        only=broker_compute_only,
        code="broker_compute_only",
        message=COMPUTE_ONLY_MSG,
    )
    return sse_error_envelope(feature=feature, error=msg)


def early_llm_sse_peel_miss(*, feature: str, error: str | None = None) -> str | None:
    if not broker_llm_enabled():
        return None
    msg = error or (
        f"{feature} stream unavailable under NIMBUSWARE_BROKER_LLM peel; "
        "broker stream path required"
    )
    _refuse_broker_only_http(
        only=broker_llm_only,
        code="broker_llm_unavailable",
        message=LLM_ONLY_MSG,
    )
    return sse_error_envelope(feature=feature, error=msg)


def sse_stream_openapi_responses(
    *,
    miss_model: type,
    not_found: dict[str, Any] | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI responses for SSE routes (200 stream + optional JSON miss schema)."""
    responses: dict[int | str, dict[str, Any]] = {
        200: {
            "description": (
                "Server-sent events. Terminal ``event: error`` carries peel miss "
                "``{via, feature, error, status}`` before the stream closes."
            ),
            "content": {
                "text/event-stream": {
                    "schema": {"type": "string"},
                    "examples": {
                        "peel_miss": {
                            "summary": "Compute peel miss",
                            "value": (
                                'event: error\n'
                                'data: {"via":"broker_miss","feature":"example",'
                                '"error":"…","status":"degraded"}\n\n'
                            ),
                        },
                    },
                },
                "application/json": {"model": miss_model},
            },
        },
    }
    if not_found is not None:
        responses[404] = not_found
    return responses
