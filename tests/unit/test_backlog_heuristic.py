from __future__ import annotations

from nimbusware_orchestrator.backlog_generator import (
    generate_heuristic_backlog,
)
from nimbusware_orchestrator.campaign_slice_selector import select_next_slice


def test_generate_heuristic_backlog_crm_template() -> None:
    backlog = generate_heuristic_backlog(
        "run-crm",
        requirements={"business_prompt": "Build a minimal CRM with auth and contacts"},
        max_slices=10,
    )
    assert backlog.metadata.generator_mode == "heuristic"
    assert backlog.metadata.total_slices_planned == 5
    selected = select_next_slice(backlog)
    assert selected is not None
    assert selected.slice.slice_id == "slice-001"
    assert "Auth" in selected.slice.rationale or "Scaffold" in selected.slice.rationale
