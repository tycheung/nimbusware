from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_profiles import load_profile_subsection


@dataclass(frozen=True)
class TheaterWorkflowBlock:
    enabled: bool = True
    max_message_chars: int = 1200
    show_evidence_links: bool = True
    llm_summary: bool = False


def _theater_from_block(block: dict[str, Any]) -> TheaterWorkflowBlock:
    return TheaterWorkflowBlock(
        enabled=bool(block.get("enabled", True)),
        max_message_chars=max(200, int(block.get("max_message_chars", 1200) or 1200)),
        show_evidence_links=bool(block.get("show_evidence_links", True)),
        llm_summary=bool(block.get("llm_summary", False)),
    )


def parse_theater_workflow_block(
    repo_root: Path,
    workflow_profile: str,
    *,
    config_materializer: Any | None = None,
) -> TheaterWorkflowBlock:
    return load_profile_subsection(
        repo_root,
        workflow_profile,
        "theater",
        _theater_from_block,
        default=TheaterWorkflowBlock(),
        config_materializer=config_materializer,
    )


def theater_effective_metadata(block: TheaterWorkflowBlock) -> dict[str, Any]:
    return {
        "enabled": block.enabled,
        "max_message_chars": block.max_message_chars,
        "show_evidence_links": block.show_evidence_links,
        "llm_summary": block.llm_summary,
    }
