from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_core.context_budget import truncate_for_llm_history
from agent_core.models.slice_handoff import SliceHandoffSummary
from orchestrator.slice.gate import SliceGateChainResult
from orchestrator.slice.micro_slice import SlicePlan


def resolve_slice_contract_ref(
    plan: SlicePlan,
    *,
    repo_root: Path | None = None,
) -> str | None:
    surface = str(plan.surface_id or "").strip().lower()
    if surface == "contract":
        from env import find_repo_root
        from orchestrator.slice.contract import run_slice_contract_check

        root = repo_root or find_repo_root()
        result = run_slice_contract_check(root, require_openapi=True)
        if result.passed and result.detail.strip():
            return result.detail.strip()
        return "openapi:pending"
    stack = str(plan.stack_id or "").strip()
    if stack:
        return f"stack:{stack}"
    if surface:
        return f"surface:{surface}"
    return None


def nimbusware_handoff_max_chars(default: int = 4000) -> int:
    from env.env_flags import nimbusware_handoff_max_chars as _max

    return _max(default=default)


def build_slice_handoff_summary(
    plan: SlicePlan,
    *,
    prior: SliceHandoffSummary | None = None,
    gate: SliceGateChainResult | None = None,
    paths_touched: tuple[str, ...] = (),
    diff_stat: str = "",
    campaign_goal: str = "",
    repo_root: Path | None = None,
) -> SliceHandoffSummary:
    goal = campaign_goal.strip() or (prior.goal if prior else plan.rationale)
    progress = list(prior.progress) if prior else []
    decisions = list(prior.key_decisions) if prior else []
    read_files = list(prior.read_files) if prior else []
    modified = list(prior.modified_files) if prior else []

    verdict = "passed" if gate is None or gate.passed else "failed"
    stat = diff_stat.strip() or f"slice {plan.slice_id}"
    progress.append(f"{plan.slice_id}: {verdict} — {stat}")

    if gate is not None and not gate.passed:
        for step in gate.steps:
            if step.verdict.upper() == "FAIL":
                decisions.append(f"{plan.slice_id}: blocked at {step.name}")

    next_steps: list[str] = []
    if gate is None or gate.passed:
        next_steps.append(f"Continue after {plan.slice_id}")
    else:
        next_steps.append(f"Address gate failure for {plan.slice_id}")

    for p in plan.target_paths:
        norm = p.replace("\\", "/").lstrip("/")
        if norm and norm not in read_files:
            read_files.append(norm)
    for p in paths_touched:
        norm = p.replace("\\", "/").lstrip("/")
        if norm and norm not in modified:
            modified.append(norm)

    return SliceHandoffSummary(
        goal=goal,
        progress=tuple(progress[-20:]),
        key_decisions=tuple(decisions[-10:]),
        next_steps=tuple(next_steps),
        read_files=tuple(read_files[-30:]),
        modified_files=tuple(modified[-30:]),
        surface_id=plan.surface_id or (prior.surface_id if prior else None),
        stack_id=plan.stack_id or (prior.stack_id if prior else None),
        contract_ref=resolve_slice_contract_ref(plan, repo_root=repo_root)
        or (prior.contract_ref if prior else None),
    )


def handoff_markdown_capped(summary: SliceHandoffSummary) -> str:
    return truncate_for_llm_history(
        summary.render_markdown(),
        max_chars=nimbusware_handoff_max_chars(),
    )


def latest_handoff_from_events(events: list[dict[str, Any]]) -> SliceHandoffSummary | None:
    latest: SliceHandoffSummary | None = None
    for row in events:
        payload = row.get("payload") or {}
        if not isinstance(payload, dict) or payload.get("stage_name") != "slice.handoff":
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        handoff_raw = meta.get("slice_handoff")
        if isinstance(handoff_raw, dict):
            latest = SliceHandoffSummary.model_validate(handoff_raw)
    return latest
