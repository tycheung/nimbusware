from __future__ import annotations

from uuid import uuid4

from agent_core.models import EventType, validate_event_dict


def test_model_binding_overridden_event_validates() -> None:
    data = {
        "event_type": EventType.MODEL_BINDING_OVERRIDDEN.value,
        "event_id": str(uuid4()),
        "run_id": str(uuid4()),
        "occurred_at": "2026-01-01T00:00:00+00:00",
        "payload": {
            "agent_role": "planner",
            "provider_id": "openai",
            "provider_kind": "cloud",
            "model_id": "gpt-4o-mini",
        },
    }
    ev = validate_event_dict(data)
    assert ev.event_type == EventType.MODEL_BINDING_OVERRIDDEN
