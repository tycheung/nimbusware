from __future__ import annotations

from uuid import UUID, uuid4

from agent_core.models import EventType, Verdict
from orchestrator.ollama_chat import extract_ollama_usage
from orchestrator.registry import RoleRegistry
from orchestrator.role_telemetry import (
    ROLE_TELEMETRY_METADATA_KEY,
    aggregate_role_telemetry_rows,
    extract_role_telemetry_hint,
    merge_role_telemetry_metadata,
)
from orchestrator.routing_suggestions import (
    enrich_aggregate_with_model_selection,
    suggest_model_routing_changes,
)


def _registry() -> RoleRegistry:
    return RoleRegistry.from_mapping(
        {
            "planner": UUID("11111111-1111-4111-8111-111111111101"),
            "backend_writer": UUID("44444444-4444-4444-8444-444444444404"),
        },
    )


def test_merge_and_extract_role_telemetry_metadata() -> None:
    meta = merge_role_telemetry_metadata(
        {},
        prompt_tokens=120,
        completion_tokens=40,
        latency_ms=900,
        model_id="llama3.1:8b",
    )
    assert ROLE_TELEMETRY_METADATA_KEY in meta
    row = {"metadata": meta}
    hint = extract_role_telemetry_hint(row)
    assert hint is not None
    assert hint["prompt_tokens"] == 120
    assert hint["completion_tokens"] == 40


def test_aggregate_role_telemetry_rows_stage_and_preflight() -> None:
    rid = uuid4()
    rows = [
        {
            "store_seq": 1,
            "run_id": rid,
            "event_type": EventType.MODEL_PREFLIGHT_PASSED.value,
            "payload": {
                "validated_model_id": "llama3.1:8b",
                "context_tokens": 8192,
                "p95_latency_ms": 7500,
            },
        },
        {
            "store_seq": 2,
            "run_id": rid,
            "event_type": EventType.STAGE_PASSED.value,
            "payload": {
                "stage_name": "implementation",
                "duration_ms": 1200,
            },
            "model_id": "llama3.1:8b",
        },
        {
            "store_seq": 3,
            "run_id": rid,
            "event_type": EventType.CRITIC_VERDICT_EMITTED.value,
            "actor_role": "11111111-1111-4111-8111-111111111101",
            "payload": {
                "critic_role": "11111111-1111-4111-8111-111111111101",
                "verdict": Verdict.PASS.value,
            },
            "metadata": merge_role_telemetry_metadata(
                {},
                prompt_tokens=50,
                completion_tokens=10,
                latency_ms=200,
            ),
        },
    ]
    doc = aggregate_role_telemetry_rows(rows, registry=_registry(), run_ids=[str(rid)])
    assert doc["run_count"] == 1
    assert doc["preflight"]["max_p95_latency_ms"] == 7500
    assert "backend_writer" in doc["roles"]
    assert doc["roles"]["backend_writer"]["stage_duration_ms"]["max"] == 1200
    assert "planner" in doc["roles"]
    assert doc["roles"]["planner"]["token_hints"]["prompt_tokens_total"] == 50


def test_extract_ollama_usage() -> None:
    usage = extract_ollama_usage(
        {
            "prompt_eval_count": 10,
            "eval_count": 20,
            "eval_duration": 2_500_000_000,
        },
    )
    assert usage["prompt_tokens"] == 10
    assert usage["completion_tokens"] == 20
    assert usage["latency_ms"] == 2500


def test_suggest_model_routing_changes_latency_cap() -> None:
    aggregate = {
        "preflight": {"max_p95_latency_ms": 7800, "avg_p95_latency_ms": 7000},
        "roles": {},
    }
    routing = {"preflight": {"max_p95_latency_ms": 8000}}
    suggestions = suggest_model_routing_changes(aggregate, routing)
    fields = [s["field"] for s in suggestions]
    assert "preflight.max_p95_latency_ms" in fields


def test_suggest_model_routing_fallback_rate() -> None:
    aggregate = {
        "model_selection": {"primary_count": 1, "fallback_count": 4},
        "roles": {},
    }
    routing = {
        "models": {
            "primary": {"id": "llama3.1:8b"},
            "fallbacks": [{"id": "qwen2.5-coder:14b"}],
        },
    }
    suggestions = suggest_model_routing_changes(aggregate, routing)
    assert any(s["field"] == "models.primary.id" for s in suggestions)


def test_enrich_aggregate_with_model_selection() -> None:
    aggregate = {"schema_version": 1, "roles": {}}
    rows = [
        {"event_type": "model.selected.primary"},
        {"event_type": "model.selected.fallback"},
        {"event_type": "model.selected.fallback"},
    ]
    enriched = enrich_aggregate_with_model_selection(aggregate, rows)
    assert enriched["model_selection"]["primary_count"] == 1
    assert enriched["model_selection"]["fallback_count"] == 2


def test_registry_taxonomy_key_for() -> None:
    reg = _registry()
    assert reg.taxonomy_key_for(UUID("11111111-1111-4111-8111-111111111101")) == "planner"
