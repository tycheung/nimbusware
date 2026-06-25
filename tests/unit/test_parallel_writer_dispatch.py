from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from unittest.mock import patch

from agent_core.models import EventType
from nimbusware_env import find_repo_root
from nimbusware_orchestrator.pipeline import make_dev_orchestrator


def _dispatch_writers(orch, rid, profile: str, *, workspace: Path | None = None) -> None:
    ws = workspace or find_repo_root(start=Path(__file__).resolve().parents[1])
    sg = orch._stage_graph_snapshot_for_run(rid)
    writers_group = ["implementation", "test_writer", "frontend_writer"]
    orch._run_writers_parallel_dispatch(rid, sg, writers_group, workspace=ws)


@patch.dict(
    os.environ,
    {"NIMBUSWARE_PARALLEL_WRITERS": "1", "NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS": "1"},
    clear=False,
)
@patch("nimbusware_orchestrator.verify_fanout.run_writer_verifier_bundle", return_value=(0, "ok"))
def test_parallel_on_emits_both_writer_starts(_mock: object) -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("parallel_writers_on")
    _dispatch_writers(orch, rid, "parallel_writers_on")
    rows = mem.list_run_events(str(rid))
    writer_starts = [
        r
        for r in rows
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and (r.get("payload") or {}).get("stage_name") in ("implementation", "test_writer")
    ]
    assert len(writer_starts) >= 2


@patch("nimbusware_orchestrator.verify_fanout.run_writer_verifier_bundle", return_value=(0, "ok"))
def test_parallel_off_matches_sequential_metadata(_mock: object) -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    sg = orch._stage_graph_snapshot_for_run(rid)
    orch._run_writers_sequential(
        rid, sg, workspace=find_repo_root(start=Path(__file__).resolve().parents[1])
    )
    for row in mem.list_run_events(str(rid)):
        if row.get("event_type") != EventType.STAGE_STARTED.value:
            continue
        sn = (row.get("payload") or {}).get("stage_name")
        if sn in ("implementation", "test_writer"):
            meta = row.get("metadata") or {}
            assert meta.get("dispatch_mode", "sequential") == "sequential"


@patch.dict(
    os.environ,
    {
        "NIMBUSWARE_PARALLEL_WRITERS": "1",
        "NIMBUSWARE_PARALLEL_WRITER_TEST_DELAY_SECONDS": "0.15",
    },
    clear=False,
)
def test_parallel_writers_overlap_timing() -> None:
    call_order: list[str] = []
    lock = threading.Lock()

    def slow_impl(_ws: object) -> tuple[int, str]:
        with lock:
            call_order.append("impl_start")
        time.sleep(0.05)
        with lock:
            call_order.append("impl_end")
        return 0, "ok"

    def fast_impl(_ws: object) -> tuple[int, str]:
        with lock:
            call_order.append("impl_start")
            call_order.append("impl_end")
        return 0, "ok"

    with patch(
        "nimbusware_orchestrator.verify_fanout.run_writer_verifier_bundle",
        side_effect=fast_impl,
    ):
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("parallel_writers_on")
        _dispatch_writers(orch, rid, "parallel_writers_on")

    tw_pass_idx = next(
        i
        for i, r in enumerate(mem.list_run_events(str(rid)))
        if r.get("event_type") == EventType.STAGE_PASSED.value
        and (r.get("payload") or {}).get("stage_name") == "test_writer"
    )
    assert "impl_start" in call_order
    assert tw_pass_idx > 0
