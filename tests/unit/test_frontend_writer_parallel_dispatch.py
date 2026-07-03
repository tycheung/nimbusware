from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from agent_core.models import EventType
from agent_core.stage_graph import parallel_group_members
from env import find_repo_root
from orchestrator.pipeline import make_dev_orchestrator


@patch.dict(os.environ, {"NIMBUSWARE_PARALLEL_WRITERS": "1"}, clear=False)
def test_frontend_writer_runs_in_parallel_group() -> None:
    with patch("orchestrator.verify_fanout.run_writer_verifier_bundle", return_value=(0, "ok")):
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("parallel_writers_on")
        ws = find_repo_root(start=Path(__file__).resolve().parents[1])
        sg = orch._stage_graph_snapshot_for_run(rid)
        writers_group = parallel_group_members(sg, "writers") if sg else []
        orch._run_writers_parallel_dispatch(rid, sg, writers_group, workspace=ws)
    rows = mem.list_run_events(str(rid))
    starts = [
        (r.get("payload") or {}).get("stage_name")
        for r in rows
        if r.get("event_type") == EventType.STAGE_STARTED.value
    ]
    assert "frontend_writer" in starts
    assert "implementation" in starts
    assert "test_writer" in starts
