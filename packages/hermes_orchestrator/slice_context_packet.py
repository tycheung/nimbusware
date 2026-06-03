"""Build capped SliceContextPacket for role handoffs."""

from __future__ import annotations

from agent_core.models.slice_packet import SliceContextPacket, SliceVerdictSummary
from hermes_orchestrator.micro_slice import SlicePlan
from hermes_orchestrator.slice_gate import SliceGateChainResult
from nimbusware_env.env_flags import hermes_slice_packet_max_chars


def default_packet_max_chars() -> int:
    return max(500, hermes_slice_packet_max_chars())


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
