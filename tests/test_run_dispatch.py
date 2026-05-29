"""Run dispatch queue boundary (plan §12 Phase 2-d)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from hermes_orchestrator.pipeline import make_dev_orchestrator
from hermes_orchestrator.run_dispatch import (
    InMemoryRunQueue,
    RedisRunQueue,
    RunDispatchTask,
    get_run_queue,
    set_run_queue,
)
from hermes_orchestrator.run_worker import run_worker_loop

ROOT = Path(__file__).resolve().parents[1]


def test_in_memory_enqueue_dequeue_ack() -> None:
    q = InMemoryRunQueue()
    task = RunDispatchTask(run_id=str(uuid4()), step="verify", payload={"k": "v"})
    q.enqueue(task)
    got = q.dequeue()
    assert got is not None
    assert got.task_id == task.task_id
    assert q.ack(task.task_id) is True
    assert q.ack(task.task_id) is True


def test_dispatch_off_runs_sync() -> None:
    orch, _mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    with patch.object(orch, "execute_writer_verifier_pass") as mock_exec:
        mode = orch.dispatch_or_run_verify(rid)
    assert mode == "sync"
    mock_exec.assert_called_once()


@patch.dict(os.environ, {"HERMES_RUN_DISPATCH": "memory"}, clear=False)
def test_dispatch_on_enqueues_without_sync_execute() -> None:
    set_run_queue(InMemoryRunQueue())
    orch, _mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    with patch.object(orch, "execute_writer_verifier_pass") as mock_exec:
        mode = orch.dispatch_or_run_verify(rid)
    assert mode == "queued"
    mock_exec.assert_not_called()
    task = get_run_queue().dequeue()
    assert task is not None
    assert task.step == "verify"
    assert task.run_id == str(rid)


@patch.dict(os.environ, {"HERMES_RUN_DISPATCH": "memory"}, clear=False)
def test_process_verify_dispatch_task_drains_queue() -> None:
    set_run_queue(InMemoryRunQueue())
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    with patch(
        "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
        return_value=(0, "ok"),
    ):
        orch.dispatch_or_run_verify(rid)
        task = get_run_queue().dequeue()
        assert task is not None
        orch.process_verify_dispatch_task(task)
        get_run_queue().ack(task.task_id)
    assert any(
        r.get("event_type") == "stage.started"
        and (r.get("payload") or {}).get("stage_name") == "implementation"
        for r in mem.list_run_events(str(rid))
    )


class _FakeRedis:
    def __init__(self) -> None:
        self.pending: list[str] = []
        self.in_flight: dict[str, str] = {}

    def lpush(self, _key: str, value: str) -> None:
        self.pending.insert(0, value)

    def brpop(self, _key: str, timeout: int = 1) -> tuple[str, str] | None:
        _ = timeout
        if not self.pending:
            return None
        return ("queue", self.pending.pop())

    def hset(self, _key: str, field: str, value: str) -> None:
        self.in_flight[field] = value

    def hdel(self, _key: str, field: str) -> int:
        if field in self.in_flight:
            del self.in_flight[field]
            return 1
        return 0


    def llen(self, _key: str) -> int:
        return len(self.pending)

    def hlen(self, _key: str) -> int:
        return len(self.in_flight)


def test_redis_run_queue_enqueue_dequeue_ack() -> None:
    fake = _FakeRedis()
    q = RedisRunQueue("redis://example", client=fake)
    task = RunDispatchTask(run_id=str(uuid4()), step="verify", payload={"x": 1})
    q.enqueue(task)
    got = q.dequeue()
    assert got is not None
    assert got.task_id == task.task_id
    assert got.payload == {"x": 1}
    assert q.ack(task.task_id) is True
    assert q.ack(task.task_id) is False


@patch.dict(os.environ, {"HERMES_RUN_DISPATCH": "memory"}, clear=False)
def test_worker_loop_processes_verify_tasks() -> None:
    queue = InMemoryRunQueue()
    set_run_queue(queue)
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("default")
    queue.enqueue(RunDispatchTask(run_id=str(rid), step="verify", payload={}))
    with patch(
        "hermes_orchestrator.pipeline.run_writer_verifier_bundle",
        return_value=(0, "ok"),
    ):
        processed = run_worker_loop(queue, orch, max_tasks=1, idle_sleep_seconds=0.0)
    assert processed == 1
    assert any(
        r.get("event_type") == "stage.started"
        and (r.get("payload") or {}).get("stage_name") == "implementation"
        for r in mem.list_run_events(str(rid))
    )


def test_worker_loop_stops_after_max_idle_loops(tmp_path) -> None:
    queue = InMemoryRunQueue()
    orch, _mem = make_dev_orchestrator()
    hb = tmp_path / "worker_heartbeat.json"
    processed = run_worker_loop(
        queue,
        orch,
        max_tasks=None,
        idle_sleep_seconds=0.0,
        max_idle_loops=2,
        heartbeat_path=hb,
    )
    assert processed == 0
    payload = json.loads(hb.read_text(encoding="utf-8"))
    assert payload["status"] == "idle"
    assert payload["idle_loops"] >= 2
    assert payload["processed"] == 0


def test_run_dispatch_worker_wrapper_smoke(tmp_path: Path) -> None:
    hb = tmp_path / "worker_heartbeat.json"
    env = {**os.environ, "NIMBUSWARE_REPO_ROOT": str(ROOT), "HERMES_SKIP_PREFLIGHT": "1"}
    proc = subprocess.run(
        [
            "poetry",
            "run",
            "python",
            str(ROOT / "scripts" / "run_dispatch_worker.py"),
            "--max-idle-loops",
            "1",
            "--idle-sleep-seconds",
            "0",
            "--heartbeat-path",
            str(hb),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    payload = json.loads(hb.read_text(encoding="utf-8"))
    assert payload["status"] == "idle"


def test_run_dispatch_worker_wrapper_help_lists_runbook_flags() -> None:
    proc = subprocess.run(
        [
            "poetry",
            "run",
            "python",
            str(ROOT / "scripts" / "run_dispatch_worker.py"),
            "--help",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--max-idle-loops" in proc.stdout
    assert "--heartbeat-path" in proc.stdout
