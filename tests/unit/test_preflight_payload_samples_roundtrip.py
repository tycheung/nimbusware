from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_core.models.events import ModelPreflightPassedPayload


def test_payload_accepts_samples_list_happy_path() -> None:
    p = ModelPreflightPassedPayload(
        provider="ollama",
        validated_model_id="llama3.1:8b",
        context_tokens=8192,
        p95_latency_ms=135,
        checks_passed=["runtime_reachable", "model_available"],
        preflight_latency_sample_count=3,
        p95_latency_source="max(health_p95_ms,show_latency_ms)",
        health_latency_samples_ms=[120, 130, 135],
    )
    assert p.health_latency_samples_ms == [120, 130, 135]


def test_payload_defaults_samples_to_none_for_backward_compat() -> None:
    """Legacy callers that don't pass the field still validate fine."""
    p = ModelPreflightPassedPayload(
        provider="ollama",
        validated_model_id="llama3.1:8b",
        context_tokens=8192,
        p95_latency_ms=135,
    )
    assert p.health_latency_samples_ms is None


def test_payload_rejects_too_many_samples() -> None:
    """The cap of 20 mirrors the orchestrator-side ``_latency_sample_count`` clamp."""
    with pytest.raises(ValidationError):
        ModelPreflightPassedPayload(
            provider="ollama",
            validated_model_id="llama3.1:8b",
            context_tokens=8192,
            p95_latency_ms=135,
            health_latency_samples_ms=list(range(21)),
        )


def test_payload_rejects_negative_sample() -> None:
    with pytest.raises(ValidationError):
        ModelPreflightPassedPayload(
            provider="ollama",
            validated_model_id="llama3.1:8b",
            context_tokens=8192,
            p95_latency_ms=135,
            health_latency_samples_ms=[100, -5, 200],
        )


def test_payload_rejects_non_int_sample() -> None:
    """Pydantic coerces numeric strings to int, but truly non-numeric values must be rejected.

    The ``field_validator`` ensures non-int / non-coercible entries
    surface as ``ValidationError`` rather than silently corrupting the
    persisted payload. ``"300"`` would coerce to 300 (Pydantic default), so
    we use a nested list which is genuinely non-coercible.
    """
    with pytest.raises(ValidationError):
        ModelPreflightPassedPayload(
            provider="ollama",
            validated_model_id="llama3.1:8b",
            context_tokens=8192,
            p95_latency_ms=135,
            health_latency_samples_ms=[100, 200, [300]],  # type: ignore[list-item]
        )


def test_payload_json_round_trip_preserves_samples() -> None:
    """JSONB persistence verifies via model_dump_json → model_validate_json round-trip."""
    original = ModelPreflightPassedPayload(
        provider="ollama",
        validated_model_id="llama3.1:8b",
        context_tokens=8192,
        p95_latency_ms=135,
        checks_passed=["runtime_reachable"],
        preflight_latency_sample_count=3,
        p95_latency_source="max(...)",
        health_latency_samples_ms=[120, 130, 135],
    )
    serialized = original.model_dump_json()
    rehydrated = ModelPreflightPassedPayload.model_validate_json(serialized)
    assert rehydrated == original
    assert rehydrated.health_latency_samples_ms == [120, 130, 135]
