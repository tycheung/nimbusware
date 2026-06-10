from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_scan_critique import (
    ScanCritiqueBlock as PerformanceCritiqueBlock,
    parse_scan_critique_workflow_block as _parse,
    scan_critique_effective,
    scan_critique_llm_effective,
)


def parse_performance_critique_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> PerformanceCritiqueBlock:
    return _parse(
        repo_root,
        workflow_profile,
        "performance_critique",
        config_materializer=config_materializer,
    )


def performance_critique_effective(block: PerformanceCritiqueBlock) -> bool:
    return scan_critique_effective(block, "NIMBUSWARE_PERFORMANCE_CRITIQUE")


def performance_critique_llm_branch_effective(block: PerformanceCritiqueBlock) -> bool:
    return scan_critique_llm_effective(block, "NIMBUSWARE_PERFORMANCE_CRITIQUE_LLM")
