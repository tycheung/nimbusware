from __future__ import annotations

PREFLIGHT_DISPLAY_FIELDS: tuple[tuple[str, str], ...] = (
    ("validated_model_id", "Validated model id"),
    ("provider", "Provider"),
    ("context_tokens", "Context tokens"),
    ("p95_latency_ms", "p95 latency (ms)"),
    ("preflight_latency_sample_count", "Samples used"),
    ("p95_latency_source", "p95 source"),
    ("checks_passed", "Checks passed"),
    ("event_id", "Event id"),
    ("occurred_at", "Occurred at"),
)

__all__ = ["PREFLIGHT_DISPLAY_FIELDS"]
