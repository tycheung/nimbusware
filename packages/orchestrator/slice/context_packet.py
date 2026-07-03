from __future__ import annotations

from pathlib import Path

from agent_core.models.slice_packet import SliceContextPacket, SliceVerdictSummary
from env.env_flags import (
    nimbusware_slice_packet_max_chars,
    nimbusware_slice_repo_map_enabled,
    nimbusware_slice_repo_map_max_chars,
)
from orchestrator.slice.gate import SliceGateChainResult
from orchestrator.slice.handoff import resolve_slice_contract_ref
from orchestrator.slice.micro_slice import SlicePlan


def default_packet_max_chars() -> int:
    return max(500, nimbusware_slice_packet_max_chars())


def build_slice_context_packet(
    plan: SlicePlan,
    *,
    diff_unified: str = "",
    test_output: str = "",
    gate: SliceGateChainResult | None = None,
    policy_excerpt: str = "",
    memory_excerpt: str = "",
    repo_map_excerpt: str = "",
    handoff_summary: str = "",
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
        and nimbusware_slice_repo_map_enabled()
    ):
        from orchestrator.slice.repo_map import build_repo_map_excerpt

        repo_excerpt = build_repo_map_excerpt(
            repo_root,
            plan.target_paths,
            max_chars=nimbusware_slice_repo_map_max_chars(),
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
        handoff_summary=handoff_summary,
        surface_id=plan.surface_id,
        stack_id=plan.stack_id,
        contract_ref=resolve_slice_contract_ref(plan, repo_root=repo_root),
    )
    cap = max_chars if max_chars is not None else default_packet_max_chars()
    return packet.capped(max_chars=cap)
