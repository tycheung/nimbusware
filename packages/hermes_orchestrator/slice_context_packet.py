"""Build capped SliceContextPacket for role handoffs."""

from __future__ import annotations

import os

from agent_core.models.slice_packet import SliceContextPacket, SliceVerdictSummary
from hermes_orchestrator.micro_slice import SlicePlan
from hermes_orchestrator.slice_gate import SliceGateChainResult


def default_packet_max_chars() -> int:
    raw = os.environ.get("HERMES_SLICE_PACKET_MAX_CHARS", "12000").strip()
    try:
        return max(500, int(raw))
    except ValueError:
        return 12000


def build_slice_context_packet(
    plan: SlicePlan,
    *,
    diff_unified: str = "",
    test_output: str = "",
    gate: SliceGateChainResult | None = None,
    policy_excerpt: str = "",
    memory_excerpt: str = "",
    max_chars: int | None = None,
) -> SliceContextPacket:
    verdicts: list[SliceVerdictSummary] = []
    if gate is not None:
        for step in gate.steps:
            verdicts.append(
                SliceVerdictSummary(
                    critic_role=step.name,
                    verdict=step.verdict,
                    severity=None,
                ),
            )
    packet = SliceContextPacket(
        slice_id=plan.slice_id,
        paths=plan.target_paths,
        diff_unified=diff_unified,
        test_output=test_output,
        prior_verdicts=tuple(verdicts),
        policy_excerpt=policy_excerpt,
        memory_excerpt=memory_excerpt,
    )
    cap = max_chars if max_chars is not None else default_packet_max_chars()
    return packet.capped(max_chars=cap)
