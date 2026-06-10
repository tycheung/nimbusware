from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_scan_critique import (
    ScanCritiqueBlock as SecurityCritiqueBlock,
)
from nimbusware_orchestrator.workflow_scan_critique import (
    parse_scan_critique_workflow_block as _parse,
)
from nimbusware_orchestrator.workflow_scan_critique import (
    scan_critique_effective,
    scan_critique_llm_effective,
)


def parse_security_critique_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> SecurityCritiqueBlock:
    return _parse(
        repo_root,
        workflow_profile,
        "security_critique",
        config_materializer=config_materializer,
    )


def security_critique_effective(block: SecurityCritiqueBlock) -> bool:
    return scan_critique_effective(block, "NIMBUSWARE_SECURITY_CRITIQUE")


def security_critique_llm_branch_effective(block: SecurityCritiqueBlock) -> bool:
    return scan_critique_llm_effective(block, "NIMBUSWARE_SECURITY_CRITIQUE_LLM")
