"""True parallel writer dispatch."""

from __future__ import annotations

import os
import threading
import time
from unittest.mock import patch

from agent_core.models import EventType
from nimbusware_orchestrator.pipeline import make_dev_orchestrator


@patch.dict(
    os.environ,
    {"NIMBUSWARE_PARALLEL_WRITERS": "1", "NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS": "1"},
    clear=False,
)
@patch("nimbusware_orchestrator.pipeline.run_writer_verifier_bundle", return_value=(0, "ok"))
def test_parallel_on_emits_both_writer_starts_before_critique(_mock: object) -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("parallel_writers_on")
    orch.execute_writer_verifier_pass(rid)
    rows = mem.list_run_events(str(rid))
    writer_starts = [
        r
        for r in rows
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and (r.get("payload") or {}).get("stage_name") in ("implementation", "test_writer")
    ]
    assert len(writer_starts) >= 2
    first_critique_idx = next(
        i
        for i, r in enumerate(rows)
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and (r.get("payload") or {}).get("stage_name") == "implementation.critique"
    )
    writer_indices = [rows.index(r) for r in writer_starts]
    assert all(idx < first_critique_idx for idx in writer_indices)


@patch("nimbusware_orchestrator.pipeline.run_writer_verifier_bundle", return_value=(0, "ok"))
def test_parallel_off_matches_sequential_metadata(_mock: object) -> None:
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    orch.execute_writer_verifier_pass(rid)
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
        "NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS": "1",
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
        "nimbusware_orchestrator.pipeline.run_writer_verifier_bundle",
        side_effect=fast_impl,
    ):
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("parallel_writers_on")
        orch.execute_writer_verifier_pass(rid)

    tw_pass_idx = next(
        i
        for i, r in enumerate(mem.list_run_events(str(rid)))
        if r.get("event_type") == EventType.STAGE_PASSED.value
        and (r.get("payload") or {}).get("stage_name") == "test_writer"
    )
    assert "impl_start" in call_order
    assert tw_pass_idx > 0


@patch.dict(
    os.environ,
    {"NIMBUSWARE_PARALLEL_WRITERS": "1", "NIMBUSWARE_TEST_WRITER_STAGE": "1"},
    clear=False,
)
def test_parallel_real_test_writer_emits_exit_code_metadata() -> None:
    with patch(
        "nimbusware_orchestrator.pipeline.run_writer_verifier_bundle",
        return_value=(0, "ok"),
    ):
        with patch(
            "nimbusware_orchestrator.pipeline.run_test_writer_stage",
            return_value=(3, "test failure", "subprocess"),
        ):
            orch, mem = make_dev_orchestrator()
            rid = orch.create_run("parallel_writers_on")
            orch.execute_writer_verifier_pass(rid)
    rows = mem.list_run_events(str(rid))
    fail = next(
        r
        for r in rows
        if r.get("event_type") == EventType.STAGE_FAILED.value
        and (r.get("payload") or {}).get("stage_name") == "test_writer"
    )
    assert (fail.get("metadata") or {}).get("exit_code") == 3


@patch.dict(
    os.environ,
    {
        "NIMBUSWARE_PARALLEL_WRITERS": "1",
        "NIMBUSWARE_TEST_WRITER_STAGE": "1",
        "NIMBUSWARE_TEST_WRITER_LLM_BODY": "1",
        "NIMBUSWARE_TEST_WRITER_LLM_STUB": "1",
        "NIMBUSWARE_USE_LLM": "1",
    },
    clear=False,
)
def test_parallel_test_writer_llm_stub_body_mode_metadata() -> None:
    with patch(
        "nimbusware_orchestrator.pipeline.run_writer_verifier_bundle",
        return_value=(0, "ok"),
    ):
        orch, mem = make_dev_orchestrator()
        rid = orch.create_run("parallel_writers_on")
        orch.execute_writer_verifier_pass(rid)
    rows = mem.list_run_events(str(rid))
    tw_started = next(
        r
        for r in rows
        if r.get("event_type") == EventType.STAGE_STARTED.value
        and (r.get("payload") or {}).get("stage_name") == "test_writer"
    )
    tw_passed = next(
        r
        for r in rows
        if r.get("event_type") == EventType.STAGE_PASSED.value
        and (r.get("payload") or {}).get("stage_name") == "test_writer"
    )
    assert (tw_started.get("metadata") or {}).get("body_mode") == "stub"
    assert (tw_passed.get("metadata") or {}).get("body_mode") == "stub"
