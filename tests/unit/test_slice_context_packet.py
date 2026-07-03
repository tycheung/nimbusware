from __future__ import annotations

from orchestrator.micro_slice import parse_slice_plan
from orchestrator.slice_context_packet import build_slice_context_packet
from orchestrator.slice_gate import run_slice_gate_chain


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


def test_packet_preserves_memory_excerpt() -> None:
    plan = parse_slice_plan({"slice_id": "slice-abc", "target_paths": []})
    packet = build_slice_context_packet(
        plan,
        memory_excerpt="prior failure: sql injection",
        max_chars=5000,
    )
    assert "sql injection" in packet.memory_excerpt


def test_packet_includes_repo_map_when_root_provided(tmp_path) -> None:
    (tmp_path / "target.py").write_text("def run() -> None:\n    pass\n", encoding="utf-8")
    plan = parse_slice_plan({"slice_id": "s-map", "target_paths": ["target.py"]})
    packet = build_slice_context_packet(
        plan,
        repo_root=tmp_path,
        max_chars=8000,
    )
    assert packet.repo_map_excerpt
    assert packet.char_count() <= 8500


def test_packet_includes_handoff_summary() -> None:
    plan = parse_slice_plan({"slice_id": "s-h", "target_paths": ["a.py"]})
    packet = build_slice_context_packet(
        plan,
        handoff_summary="## Goal\ncampaign\n",
        max_chars=3000,
    )
    assert "campaign" in packet.handoff_summary


def test_packet_includes_surface_refs() -> None:
    plan = parse_slice_plan(
        {
            "slice_id": "s-surf",
            "target_paths": ["frontend/App.tsx"],
            "surface_id": "web",
            "stack_id": "react_vite",
        },
    )
    packet = build_slice_context_packet(plan, max_chars=3000)
    assert packet.surface_id == "web"
    assert packet.stack_id == "react_vite"
    assert packet.contract_ref == "stack:react_vite"
