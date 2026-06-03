"""Parse workflow ``probation_automation`` block for persona shelf automation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hermes_extensions.phase2 import AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD
from hermes_orchestrator.workflow_profiles import workflow_profile_dict


@dataclass(frozen=True)
class ProbationAutomationWorkflowBlock:
    enabled: bool = False
    auto_shelve: bool = True
    notify_before_promote: bool = True
    min_eval_runs: int = 2
    min_score: float = AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD
    max_below_ratio: float = 0.5
    history_run_limit: int = 20


def parse_probation_automation_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> ProbationAutomationWorkflowBlock:
    if workflow_profile is None or not str(workflow_profile).strip():
        return ProbationAutomationWorkflowBlock()
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return ProbationAutomationWorkflowBlock()
    block = raw.get("probation_automation")
    if not isinstance(block, dict):
        return ProbationAutomationWorkflowBlock()
    enabled = bool(block.get("enabled", False))
    auto_shelve = bool(block.get("auto_shelve", True))
    notify = bool(block.get("notify_before_promote", True))
    try:
        min_runs = int(block.get("min_eval_runs", 2) or 2)
    except (TypeError, ValueError):
        min_runs = 2
    min_score_raw = block.get("min_score")
    try:
        min_score = float(min_score_raw)
    except (TypeError, ValueError):
        min_score = AGENT_EVALUATOR_PROMOTION_SCORE_THRESHOLD
    max_below_raw = block.get("max_below_ratio")
    try:
        max_below = float(max_below_raw)
    except (TypeError, ValueError):
        max_below = 0.5
    hist_raw = block.get("history_run_limit")
    try:
        history_run_limit = int(hist_raw)
    except (TypeError, ValueError):
        history_run_limit = 20
    return ProbationAutomationWorkflowBlock(
        enabled=enabled,
        auto_shelve=auto_shelve,
        notify_before_promote=notify,
        min_eval_runs=max(1, min_runs),
        min_score=max(0.0, min(1.0, min_score)),
        max_below_ratio=max(0.0, min(1.0, max_below)),
        history_run_limit=max(1, history_run_limit),
    )


def probation_automation_effective_metadata(
    block: ProbationAutomationWorkflowBlock,
) -> dict[str, Any]:
    return {
        "enabled": block.enabled,
        "auto_shelve": block.auto_shelve,
        "notify_before_promote": block.notify_before_promote,
        "min_eval_runs": block.min_eval_runs,
        "min_score": block.min_score,
        "max_below_ratio": block.max_below_ratio,
        "history_run_limit": block.history_run_limit,
    }
