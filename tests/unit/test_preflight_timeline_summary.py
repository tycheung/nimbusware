from __future__ import annotations

from typing import Any

from nimbusware_api.preflight_read_model import preflight_timeline_summary


def _passed_event(
    *,
    event_id: str = "11111111-1111-4111-8111-111111111111",
    occurred_at: str = "2026-05-12T20:00:00+00:00",
    provider: str = "ollama",
    validated_model_id: str = "llama3.1:8b",
    context_tokens: int = 8192,
    p95_latency_ms: int = 135,
    samples_count: int | None = 3,
    p95_source: str | None = "max(health_p95_ms,show_latency_ms,optional_json_probe)",
    checks_passed: list[str] | None = None,
    health_samples: list[int] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "provider": provider,
        "validated_model_id": validated_model_id,
        "context_tokens": context_tokens,
        "p95_latency_ms": p95_latency_ms,
        "preflight_latency_sample_count": samples_count,
        "p95_latency_source": p95_source,
        "checks_passed": list(checks_passed or []),
    }
    if health_samples is not None:
        payload["health_latency_samples_ms"] = health_samples
    return {
        "event_type": "model.preflight.passed",
        "event_id": event_id,
        "occurred_at": occurred_at,
        "payload": payload,
    }


def test_empty_event_list_returns_none() -> None:
    assert preflight_timeline_summary([]) is None


def test_no_passed_event_returns_none() -> None:
    events = [
        {
            "event_type": "model.preflight.started",
            "event_id": "abc",
            "occurred_at": "2026-05-12T20:00:00+00:00",
            "payload": {"provider": "ollama"},
        },
        {
            "event_type": "stage.started",
            "event_id": "def",
            "occurred_at": "2026-05-12T20:01:00+00:00",
            "payload": {"stage_name": "planner"},
        },
    ]
    assert preflight_timeline_summary(events) is None


def test_single_event_projects_all_canonical_fields() -> None:
    samples = [120, 130, 135]
    ev = _passed_event(
        checks_passed=[
            "runtime_reachable",
            "model_available",
            "health_latency_measured",
            "health_latency_multisample",
            "context_budget_ok",
        ],
        health_samples=samples,
    )
    out = preflight_timeline_summary([ev])
    assert out is not None
    assert out["event_id"] == "11111111-1111-4111-8111-111111111111"
    assert out["occurred_at"] == "2026-05-12T20:00:00+00:00"
    assert out["provider"] == "ollama"
    assert out["validated_model_id"] == "llama3.1:8b"
    assert out["context_tokens"] == 8192
    assert out["p95_latency_ms"] == 135
    assert out["preflight_latency_sample_count"] == 3
    assert out["p95_latency_source"] == "max(health_p95_ms,show_latency_ms,optional_json_probe)"
    assert out["checks_passed"] == [
        "runtime_reachable",
        "model_available",
        "health_latency_measured",
        "health_latency_multisample",
        "context_budget_ok",
    ]
    assert out["health_latency_samples_ms"] == samples


def test_multiple_passed_events_latest_wins() -> None:
    """Last appended event wins (matches sibling timeline-summary convention)."""
    older = _passed_event(
        event_id="01010101-0101-4101-8101-010101010101",
        occurred_at="2026-05-12T20:00:00+00:00",
        validated_model_id="llama3.1:8b",
        p95_latency_ms=100,
        health_samples=[90, 100, 110],
    )
    newer = _passed_event(
        event_id="02020202-0202-4202-8202-020202020202",
        occurred_at="2026-05-12T20:05:00+00:00",
        validated_model_id="qwen2.5-coder:14b",
        p95_latency_ms=200,
        health_samples=[180, 200, 220],
    )
    out = preflight_timeline_summary([older, newer])
    assert out is not None
    assert out["event_id"] == "02020202-0202-4202-8202-020202020202"
    assert out["validated_model_id"] == "qwen2.5-coder:14b"
    assert out["p95_latency_ms"] == 200
    assert out["health_latency_samples_ms"] == [180, 200, 220]


def test_legacy_event_without_samples_field_projects_none() -> None:
    """Events without ``health_latency_samples_ms`` yield None projection."""
    legacy = _passed_event(health_samples=None)
    out = preflight_timeline_summary([legacy])
    assert out is not None
    # Key MUST be present (projection always exposes it) but value is None
    assert "health_latency_samples_ms" in out
    assert out["health_latency_samples_ms"] is None


def test_non_dict_payload_defensively_projects_nones() -> None:
    """Malformed payload (non-dict) should not crash; each field projects None."""
    bad = {
        "event_type": "model.preflight.passed",
        "event_id": "abc",
        "occurred_at": "2026-05-12T20:00:00+00:00",
        "payload": "this-is-not-a-dict",
    }
    out = preflight_timeline_summary([bad])
    assert out is not None
    assert out["event_id"] == "abc"
    assert out["provider"] is None
    assert out["validated_model_id"] is None
    assert out["context_tokens"] is None
    assert out["p95_latency_ms"] is None
    assert out["preflight_latency_sample_count"] is None
    assert out["p95_latency_source"] is None
    # checks_passed: defensive empty list (pl.get(...) or [])
    assert out["checks_passed"] == []
    assert out["health_latency_samples_ms"] is None
