from __future__ import annotations

from orchestrator.collab_binding_resolver import (
    merge_participant_binding,
    participant_binding_overrides,
)
from orchestrator.model_binding_resolver import ModelBindingResolver
from orchestrator.participant_output_packet import ParticipantOutputPacket


def test_participant_output_packet_caps() -> None:
    pkt = ParticipantOutputPacket(
        user_id="u1",
        agent_role="backend_writer",
        stage="slice.implement",
        model_id="gpt-4o-mini",
        summary="ok",
    )
    wire = pkt.to_wire_dict()
    assert wire["user_id"] == "u1"
    assert wire["model_id"] == "gpt-4o-mini"


def test_participant_binding_merge_and_resolve(tmp_path) -> None:
    meta = merge_participant_binding(
        {},
        user_id="alice",
        agent_role="planner",
        binding={"provider_kind": "cloud", "provider_id": "openai", "model_id": "gpt-4o-mini"},
    )
    overrides = participant_binding_overrides(meta, "alice")
    resolver = ModelBindingResolver(tmp_path)
    binding = resolver.resolve("planner", participant_overrides=overrides)
    assert binding.model_id == "gpt-4o-mini"
    assert binding.binding_source == "collab.participant_binding"
