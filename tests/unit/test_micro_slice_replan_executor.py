from __future__ import annotations

import os
from unittest.mock import patch
from uuid import UUID

from agent_core.models import EventType
from orchestrator.pipeline import make_dev_orchestrator
from orchestrator.slice.diff import SliceDiffStats
from orchestrator.slice.executor import execute_micro_slice_pass
from orchestrator.slice.micro_slice import DiffBudgetResult


@patch.dict(os.environ, {"NIMBUSWARE_MICRO_SLICE_COUNT": "1"}, clear=False)
@patch(
    "orchestrator.slice.executor.collect_slice_diff_stats",
)
@patch(
    "orchestrator.slice.executor._run_slice_verify_and_test",
    return_value=(True, "ok", True, "ok"),
)
def test_slice_replan_emitted_on_budget_fail(
    _verify: object,
    mock_stats: object,
) -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("micro_slice")

    def _stats(_ws: object, plan: object) -> SliceDiffStats:
        paths = getattr(plan, "target_paths", ())
        return SliceDiffStats(
            tuple(paths),
            loc_added=500,
            loc_removed=0,
            unified_diff="",
            source="test",
        )

    mock_stats.side_effect = _stats

    with patch(
        "orchestrator.slice.executor.check_slice_diff_budget",
    ) as mock_budget:
        mock_budget.side_effect = [
            DiffBudgetResult(False, 3, 500, "over loc"),
            DiffBudgetResult(True, 1, 10, "ok"),
            DiffBudgetResult(True, 1, 10, "ok"),
        ]
        execute_micro_slice_pass(orch, UUID(str(rid)))

    stages = [
        (r.get("payload") or {}).get("stage_name")
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == EventType.STAGE_STARTED.value
    ]
    assert "slice.replan" in stages
