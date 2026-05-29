"""Slice context packets (fo154)."""

from __future__ import annotations

from agent_core.models.slice_packet import SliceContextPacket
from hermes_orchestrator.micro_slice import parse_slice_plan
from hermes_orchestrator.slice_context_packet import build_slice_context_packet
from hermes_orchestrator.slice_gate import run_slice_gate_chain


def test_packet_caps_size() -> None:
    plan = parse_slice_plan({"slice_id": "s1", "target_paths": ["a.py"]})
    gate = run_slice_gate_chain(plan, verify_ok=True, critique_verdicts=["PASS"])
    packet = build_slice_context_packet(
        plan,
        diff_unified="x" * 50000,
        test_output="y" * 50000,
        gate=gate,
        max_chars=2000,
    )
    assert packet.char_count() <= 2500


def test_packet_preserves_slice_id() -> None:
    plan = parse_slice_plan({"slice_id": "slice-abc", "target_paths": []})
    packet = SliceContextPacket(slice_id=plan.slice_id, paths=plan.target_paths)
    assert packet.slice_id == "slice-abc"
