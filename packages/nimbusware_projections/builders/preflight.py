"""Build preflight timeline projection from run events."""

from __future__ import annotations

from typing import Any

from agent_core.models import EventType


def preflight_timeline_summary(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Latest ``model.preflight.passed`` projection for timeline / fleet history."""
    out: dict[str, Any] | None = None
    want = EventType.MODEL_PREFLIGHT_PASSED.value
    for ev in events:
        if ev.get("event_type") != want:
            continue
        payload = ev.get("payload")
        pl: dict[str, Any] = payload if isinstance(payload, dict) else {}
        out = {
            "event_id": ev.get("event_id"),
            "occurred_at": ev.get("occurred_at"),
            "provider": pl.get("provider"),
            "validated_model_id": pl.get("validated_model_id"),
            "context_tokens": pl.get("context_tokens"),
            "p95_latency_ms": pl.get("p95_latency_ms"),
            "preflight_latency_sample_count": pl.get("preflight_latency_sample_count"),
            "p95_latency_source": pl.get("p95_latency_source"),
            "checks_passed": list(pl.get("checks_passed") or []),
            "health_latency_samples_ms": pl.get("health_latency_samples_ms"),
        }
    return out
