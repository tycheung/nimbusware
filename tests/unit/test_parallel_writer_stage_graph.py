"""Parallel-writer stage graph metadata ."""

from __future__ import annotations

import os
from unittest.mock import patch

from agent_core.models import EventType
from nimbusware_orchestrator.pipeline import make_dev_orchestrator


@patch("nimbusware_orchestrator.pipeline.run_writer_verifier_bundle", return_value=(0, "ok"))
def test_writer_stage_started_carries_parallel_group(_mock: object) -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    orch.execute_writer_verifier_pass(rid)
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


@patch.dict(os.environ, {"NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS": "1"}, clear=False)
@patch("nimbusware_orchestrator.pipeline.run_writer_verifier_bundle", return_value=(0, "ok"))
def test_stage_graph_order_indices_monotonic_for_writer_starts(_mock: object) -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    orch.execute_writer_verifier_pass(rid)
    indices = [
        (r.get("metadata") or {}).get("stage_graph_order_index")
        for r in mem.list_run_events(str(rid))
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and (r.get("metadata") or {}).get("parallel_group") == "writers"
    ]
    assert indices == sorted(indices)
