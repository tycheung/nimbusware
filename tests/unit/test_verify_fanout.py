from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from nimbusware_orchestrator.run_dispatch import InMemoryRunQueue, set_run_queue
from nimbusware_orchestrator.run_worker import run_worker_loop
from nimbusware_orchestrator.verify_fanout import (
    dispatch_verify_shards,
    merge_verify_fanout,
    record_verify_shard_result,
    run_writer_verifier_resolved,
    wait_verify_fanout,
)


@patch.dict(
    os.environ,
    {"NIMBUSWARE_VERIFY_DISPATCH_FANOUT": "1", "NIMBUSWARE_RUN_DISPATCH": "memory"},
    clear=False,
)
def test_verify_fanout_dispatches_three_shards(tmp_path: Path) -> None:
    set_run_queue(InMemoryRunQueue())
    run_id = str(uuid4())
    fanout_id = dispatch_verify_shards(run_id, tmp_path)
    assert fanout_id is not None
    from nimbusware_orchestrator.run_dispatch import get_run_queue

    tasks = []
    while True:
        task = get_run_queue().dequeue()
        if task is None:
            break
        tasks.append(task)
    assert len(tasks) == 3
    assert {t.step for t in tasks} == {"verify_shard"}
    assert all(t.payload.get("fanout_id") == fanout_id for t in tasks)


@patch.dict(
    os.environ,
    {"NIMBUSWARE_VERIFY_DISPATCH_FANOUT": "1", "NIMBUSWARE_RUN_DISPATCH": "memory"},
    clear=False,
)
def test_verify_fanout_worker_merge(tmp_path: Path) -> None:
    queue = InMemoryRunQueue()
    set_run_queue(queue)
    run_id = str(uuid4())
    fanout_id = dispatch_verify_shards(run_id, tmp_path)
    assert fanout_id is not None
    with patch(
        "nimbusware_orchestrator.verify_fanout.run_writer_verifier_shard",
        side_effect=[(0, "pytest ok"), (0, "ruff ok"), (0, "bandit ok")],
    ):
        processed = run_worker_loop(queue, object(), max_tasks=3, idle_sleep_seconds=0.0)
    assert processed == 3
    assert wait_verify_fanout(fanout_id, timeout_seconds=1.0)
    code, log = merge_verify_fanout(fanout_id)
    assert code == 0
    assert "pytest ok" in log
    assert "bandit ok" in log


def test_verify_fanout_sync_fallback_without_dispatch(tmp_path: Path) -> None:
    with patch(
        "nimbusware_orchestrator.verify_fanout.run_writer_verifier_bundle",
        return_value=(0, "sync bundle"),
    ):
        code, log = run_writer_verifier_resolved(tmp_path, run_id=str(uuid4()))
    assert code == 0
    assert log == "sync bundle"


@patch.dict(
    os.environ,
    {"NIMBUSWARE_VERIFY_DISPATCH_FANOUT": "1", "NIMBUSWARE_RUN_DISPATCH": "memory"},
    clear=False,
)
def test_verify_fanout_timeout_merges_partial_shards(tmp_path: Path) -> None:
    fanout_id = str(uuid4())
    run_id = str(uuid4())
    record_verify_shard_result(fanout_id, "pytest", 0, "pytest ok")
    record_verify_shard_result(fanout_id, "ruff", 0, "ruff ok")
    with (
        patch(
            "nimbusware_orchestrator.verify_fanout.dispatch_verify_shards",
            return_value=fanout_id,
        ),
        patch(
            "nimbusware_orchestrator.verify_fanout.wait_verify_fanout",
            return_value=False,
        ),
    ):
        code, log = run_writer_verifier_resolved(
            tmp_path,
            run_id=run_id,
            timeout_seconds=0.01,
        )
    assert code == 1
    assert "incomplete (2/3 shards)" in log
    assert "pytest ok" in log


def test_record_and_merge_verify_fanout() -> None:
    fanout_id = str(uuid4())
    record_verify_shard_result(fanout_id, "pytest", 0, "p")
    record_verify_shard_result(fanout_id, "ruff", 1, "r")
    record_verify_shard_result(fanout_id, "bandit", 0, "b")
    assert wait_verify_fanout(fanout_id, timeout_seconds=0.1)
    code, log = merge_verify_fanout(fanout_id)
    assert code == 1
    assert "ruff" in log
