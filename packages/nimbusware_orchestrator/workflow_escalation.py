from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_profiles import (
    coerce_yaml_bool,
    load_profile_subsection,
)


@dataclass(frozen=True)
class EscalationWorkflowBlock:
    suppress_automatic_escalation: bool = False


def _escalation_from_block(block: dict[str, Any]) -> EscalationWorkflowBlock:
    return EscalationWorkflowBlock(
        suppress_automatic_escalation=coerce_yaml_bool(
            block.get("suppress_automatic_escalation", False)
        ),
    )


def parse_escalation_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> EscalationWorkflowBlock:
    return load_profile_subsection(
        repo_root,
        workflow_profile,
        "escalation",
        _escalation_from_block,
        default=EscalationWorkflowBlock(),
        config_materializer=config_materializer,
    )
