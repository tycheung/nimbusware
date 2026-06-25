from __future__ import annotations

from nimbusware_orchestrator.collab_mesh_bindings import (
    executor_binding_hint,
    participant_overrides_from_hint,
)


def test_executor_binding_hint_from_session_metadata() -> None:
    meta = {
        "collab": {
            "participant_bindings": {
                "user-a": {
                    "backend_writer": {
                        "provider_kind": "cloud",
                        "provider_id": "openai_compatible",
                        "model_id": "gpt-4o-mini",
                        "connection_id": "conn-1",
                    }
                }
            }
        }
    }
    hint = executor_binding_hint(meta, executor_user_id="user-a", agent_role="backend_writer")
    assert hint is not None
    assert hint["model_id"] == "gpt-4o-mini"
    overrides = participant_overrides_from_hint(hint, "backend_writer")
    assert overrides["backend_writer"]["connection_id"] == "conn-1"
