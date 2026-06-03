"""Build capped SliceContextPacket for role handoffs."""

from __future__ import annotations

from pathlib import Path

from agent_core.models.slice_packet import SliceContextPacket, SliceVerdictSummary
from hermes_orchestrator.micro_slice import SlicePlan
from hermes_orchestrator.slice_gate import SliceGateChainResult
from nimbusware_env.env_flags import (
    hermes_slice_packet_max_chars,
    hermes_slice_repo_map_enabled,
    hermes_slice_repo_map_max_chars,
)


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
    repo_map_excerpt: str = "",
    repo_root: Path | None = None,
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
    repo_excerpt = repo_map_excerpt
    if (
        not repo_excerpt
        and repo_root is not None
        and plan.target_paths
        and hermes_slice_repo_map_enabled()
    ):
        from hermes_orchestrator.slice_repo_map import build_repo_map_excerpt

        repo_excerpt = build_repo_map_excerpt(
            repo_root,
            plan.target_paths,
            max_chars=hermes_slice_repo_map_max_chars(),
        )
    packet = SliceContextPacket(
        slice_id=plan.slice_id,
        paths=plan.target_paths,
        diff_unified=diff_unified,
        test_output=test_output,
        prior_verdicts=tuple(verdicts),
        policy_excerpt=policy_excerpt,
        memory_excerpt=memory_excerpt,
        repo_map_excerpt=repo_excerpt,
    )
    cap = max_chars if max_chars is not None else default_packet_max_chars()
    return packet.capped(max_chars=cap)
