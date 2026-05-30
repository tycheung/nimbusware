from __future__ import annotations

import os
from unittest.mock import patch

from agent_core.models import EventType
from hermes_orchestrator.pipeline import make_dev_orchestrator


@patch.dict(os.environ, {"HERMES_PARALLEL_WRITERS": "1"}, clear=False)
def test_frontend_writer_runs_in_parallel_group() -> None:
    with patch("hermes_orchestrator.pipeline.run_writer_verifier_bundle", return_value=(0, "ok")):
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("default")
        orch.execute_writer_verifier_pass(rid)
    rows = mem.list_run_events(str(rid))
    starts = [
        (r.get("payload") or {}).get("stage_name")
        for r in rows
        if r.get("event_type") == EventType.STAGE_STARTED.value
    ]
    assert "frontend_writer" in starts
    assert "implementation" in starts
    assert "test_writer" in starts
