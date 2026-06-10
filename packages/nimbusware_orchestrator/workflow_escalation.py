from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict


@dataclass(frozen=True)
class EscalationWorkflowBlock:
    """Parsed ``escalation`` subsection from ``configs/workflows/{profile}.yaml``."""

    suppress_automatic_escalation: bool = False


def parse_escalation_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> EscalationWorkflowBlock:
    """Return workflow escalation overrides; missing block → do not suppress."""
    if workflow_profile is None or not str(workflow_profile).strip():
        return EscalationWorkflowBlock()
    key = str(workflow_profile).strip()
    try:
        raw = workflow_profile_dict(repo_root, key, materializer=config_materializer)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        return EscalationWorkflowBlock()
    block = raw.get("escalation")
    if not isinstance(block, dict):
        return EscalationWorkflowBlock()
    raw_sup = block.get("suppress_automatic_escalation", False)
    if isinstance(raw_sup, bool):
        suppress = raw_sup
    elif isinstance(raw_sup, (int, float)):
        suppress = bool(raw_sup)
    elif isinstance(raw_sup, str):
        suppress = raw_sup.strip().lower() in ("1", "true", "yes", "on")
    else:
        suppress = False
    return EscalationWorkflowBlock(suppress_automatic_escalation=suppress)
