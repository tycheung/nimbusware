"""EvolutionCoordinator — propose/score beside improvement tracks (L1 → L2 → L3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from orchestrator.improvement.diagnose_learn import latest_learning_excerpt_from_rows
from orchestrator.improvement.evolution_ledger import pending_proposals
from orchestrator.improvement.prompt_evolution import (
    promote_or_reject_prompt,
    propose_overlay_from_learning,
    score_prompt_proposal,
)
from orchestrator.improvement.skill_evolution import (
    propose_skill_from_fingerprint,
    record_skill_outcome,
    skill_ids_from_metadata,
)
from orchestrator.learnings_stitch_suggest import _diagnose_fingerprints


def after_diagnose_learn(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """L1 prompt propose; L2 skill draft when fingerprint repeats (≥2)."""
    excerpt = latest_learning_excerpt_from_rows(rows)
    result: dict[str, Any] = {"prompt": None, "skill": None}
    if excerpt.strip():
        result["prompt"] = propose_overlay_from_learning(
            store,
            run_id,
            workspace,
            excerpt=excerpt,
        )
    counts: dict[str, int] = {}
    for fp in _diagnose_fingerprints(rows):
        counts[fp] = counts.get(fp, 0) + 1
    for fp, n in counts.items():
        if n >= 2:
            result["skill"] = propose_skill_from_fingerprint(
                store,
                run_id,
                workspace,
                fingerprint=fp,
                excerpt=excerpt,
            )
            break
    return result


def after_slice_gate(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    metadata: dict[str, Any] | None,
    gate_passed: bool,
    has_p0_security: bool = False,
    gate_pass_delta: float = 0.0,
) -> None:
    """Score active skills and any pending prompt proposals."""
    skill_ids = skill_ids_from_metadata(metadata)
    if skill_ids:
        record_skill_outcome(
            store,
            run_id,
            workspace,
            skill_ids=skill_ids,
            gate_passed=gate_passed,
            has_p0=has_p0_security,
        )
    rows = store.list_run_events(str(run_id))
    for proposal in pending_proposals(rows):
        if proposal.get("layer") != "prompt":
            continue
        aid = str(proposal.get("artifact_id") or "")
        if not aid:
            continue
        score_prompt_proposal(
            store,
            run_id,
            artifact_id=aid,
            gate_pass_delta=gate_pass_delta if gate_passed else -1.0,
            has_p0_security=has_p0_security,
        )


def run_distill_artifacts(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
) -> dict[str, Any]:
    """DISTILL_ARTIFACTS track: propose-only L1/L2 (no workspace source mutate)."""
    rows = store.list_run_events(str(run_id))
    return after_diagnose_learn(store, run_id, workspace, rows)


def maybe_auto_promote_prompts(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    autopilot_level: int,
    enterprise: bool = False,
) -> list[str]:
    """Individual autopilot≥8 may auto-promote eligible prompts; Enterprise always manual."""
    if enterprise or autopilot_level < 8:
        return []
    rows = store.list_run_events(str(run_id))
    promoted: list[str] = []
    for proposal in pending_proposals(rows):
        if proposal.get("layer") != "prompt":
            continue
        aid = str(proposal.get("artifact_id") or "")
        # Need a scored event with eligible=true — check timeline
        from orchestrator.improvement.evolution_ledger import evolution_timeline_from_rows

        eligible = False
        for entry in evolution_timeline_from_rows(rows):
            if (
                entry.get("artifact_id") == aid
                and entry.get("phase") == "scored"
                and isinstance(entry.get("detail"), dict)
                and entry["detail"].get("eligible") is True
            ):
                eligible = True
        if eligible and promote_or_reject_prompt(
            store,
            run_id,
            workspace,
            artifact_id=aid,
            promote=True,
        ):
            promoted.append(aid)
    return promoted


def l1_l2_evals_blocking(rows: list[dict[str, Any]]) -> bool:
    return bool(pending_proposals(rows))
