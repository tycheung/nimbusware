from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.workflow_blocks_simple import (
    parse_theater_workflow_block,
    theater_effective_metadata,
)


def test_parse_theater_workflow_block_from_micro_slice() -> None:
    repo = Path(__file__).resolve().parents[2]
    block = parse_theater_workflow_block(repo, "micro_slice")
    assert block.enabled is True
    assert block.max_message_chars == 1200
    assert block.llm_summary is False
    meta = theater_effective_metadata(block)
    assert meta["enabled"] is True
    assert meta["show_evidence_links"] is True
