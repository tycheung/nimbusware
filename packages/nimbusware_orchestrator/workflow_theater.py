from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict


@dataclass(frozen=True)
class TheaterWorkflowBlock:
    enabled: bool = True
    max_message_chars: int = 1200
    show_evidence_links: bool = True
    llm_summary: bool = False


def parse_theater_workflow_block(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> TheaterWorkflowBlock:
    wf = workflow_profile_dict(repo_root, workflow_profile, materializer=config_materializer)
    raw = wf.get("theater")
    if not isinstance(raw, dict):
        return TheaterWorkflowBlock()
    return TheaterWorkflowBlock(
        enabled=bool(raw.get("enabled", True)),
        max_message_chars=max(200, int(raw.get("max_message_chars", 1200) or 1200)),
        show_evidence_links=bool(raw.get("show_evidence_links", True)),
        llm_summary=bool(raw.get("llm_summary", False)),
    )


def theater_effective_metadata(block: TheaterWorkflowBlock) -> dict[str, Any]:
    return {
        "enabled": block.enabled,
        "max_message_chars": block.max_message_chars,
        "show_evidence_links": block.show_evidence_links,
        "llm_summary": block.llm_summary,
    }
