from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from agent_core.models import EventType
from agent_core.stage_graph import parallel_group_members
from env import find_repo_root
from orchestrator.pipeline import make_dev_orchestrator


@patch.dict(os.environ, {"NIMBUSWARE_PARALLEL_WRITERS": "1"}, clear=False)
@patch("orchestrator.verify_fanout.run_writer_verifier_bundle", return_value=(0, "ok"))
def test_writer_stage_started_carries_parallel_group(_mock: object) -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("parallel_writers_on")
    ws = find_repo_root(start=Path(__file__).resolve().parents[1])
    sg = orch._stage_graph_snapshot_for_run(rid)
    writers_group = parallel_group_members(sg, "writers") if sg else []
    orch._run_writers_parallel_dispatch(rid, sg, writers_group, workspace=ws)
    writer_starts = [
        r
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and (r.get("payload") or {}).get("stage_name") in ("implementation", "test_writer")
    ]
    assert len(writer_starts) >= 2
    for row in writer_starts:
        meta = row.get("metadata") or {}
        assert meta.get("parallel_group") == "writers"
        assert isinstance(meta.get("stage_graph_order_index"), int)


@patch.dict(
    os.environ,
    {"NIMBUSWARE_PARALLEL_WRITERS": "1", "NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS": "1"},
    clear=False,
)
@patch("orchestrator.verify_fanout.run_writer_verifier_bundle", return_value=(0, "ok"))
def test_stage_graph_order_indices_monotonic_for_writer_starts(_mock: object) -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("parallel_writers_on")
    ws = find_repo_root(start=Path(__file__).resolve().parents[1])
    sg = orch._stage_graph_snapshot_for_run(rid)
    writers_group = parallel_group_members(sg, "writers") if sg else []
    orch._run_writers_parallel_dispatch(rid, sg, writers_group, workspace=ws)
    indices = [
        (r.get("metadata") or {}).get("stage_graph_order_index")
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and (r.get("metadata") or {}).get("parallel_group") == "writers"
    ]
    assert indices == sorted(indices)
