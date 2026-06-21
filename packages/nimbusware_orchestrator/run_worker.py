from __future__ import annotations

import argparse
import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from nimbusware_orchestrator.pipeline import RunOrchestrator
from nimbusware_orchestrator.run_dispatch import RunQueuePort, get_run_queue
from nimbusware_orchestrator.runtime_bootstrap import build_runtime_orchestrator


def build_worker_orchestrator() -> tuple[
    RunOrchestrator, threading.Event | None, threading.Thread | None
]:
    runtime = build_runtime_orchestrator(
        roles_from_db=False,
        use_materializer_registry=True,
    )
    return runtime.orchestrator, runtime.notify_stop, runtime.notify_thread


def run_worker_loop(
    queue: RunQueuePort,
    orchestrator: RunOrchestrator,
    *,
    max_tasks: int | None = None,
    idle_sleep_seconds: float = 0.1,
    max_idle_loops: int | None = None,
    heartbeat_path: Path | None = None,
) -> int:
    processed = 0
    idle_loops = 0
    started_at = datetime.now(timezone.utc)
    while max_tasks is None or processed < max_tasks:
        task = queue.dequeue()
        if task is None:
            idle_loops += 1
            if heartbeat_path is not None:
                _write_worker_heartbeat(
                    heartbeat_path,
                    processed=processed,
                    idle_loops=idle_loops,
                    status="idle",
                    started_at=started_at,
                    queue=queue,
                )
            if max_idle_loops is not None and idle_loops >= max_idle_loops:
                break
            time.sleep(idle_sleep_seconds)
            continue
        idle_loops = 0
        step = str(task.step).strip().lower()
        if step == "verify":
            from typing import Any

            host: Any = orchestrator
            host.process_verify_dispatch_task(task)
        elif step == "verify_shard":
            from nimbusware_orchestrator.verify_fanout import process_verify_shard_task

            process_verify_shard_task(task)
        elif step == "campaign_tick":
            orchestrator.process_campaign_dispatch_task(task)
        else:
            queue.ack(task.task_id)
            continue
        queue.ack(task.task_id)
        processed += 1
        if heartbeat_path is not None:
            _write_worker_heartbeat(
                heartbeat_path,
                processed=processed,
                idle_loops=idle_loops,
                status="active",
                started_at=started_at,
                queue=queue,
            )
    return processed


@dataclass
class EmbeddedDispatchWorker:
    stop: threading.Event
    thread: threading.Thread

    def shutdown(self, *, timeout: float = 15.0) -> None:
        self.stop.set()
        self.thread.join(timeout=timeout)


def start_embedded_dispatch_worker(
    orchestrator: RunOrchestrator,
    queue: RunQueuePort,
    *,
    idle_sleep_seconds: float = 0.05,
) -> EmbeddedDispatchWorker:
    stop = threading.Event()

    def _poll() -> None:
        while not stop.is_set():
            run_worker_loop(
                queue,
                orchestrator,
                max_tasks=1,
                max_idle_loops=None,
                idle_sleep_seconds=idle_sleep_seconds,
            )

    thread = threading.Thread(
        target=_poll,
        daemon=True,
        name="nimbusware-embed-dispatch-worker",
    )
    thread.start()
    return EmbeddedDispatchWorker(stop=stop, thread=thread)


def _args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Nimbusware agent run-dispatch worker")
    p.add_argument(
        "--max-tasks",
        type=int,
        default=None,
        help="Stop after processing N verify tasks (default: run forever)",
    )
    p.add_argument(
        "--idle-sleep-seconds",
        type=float,
        default=0.1,
        help="Sleep duration between empty queue polls",
    )
    p.add_argument(
        "--max-idle-loops",
        type=int,
        default=None,
        help="Stop after N consecutive empty queue polls (safe drain)",
    )
    p.add_argument(
        "--heartbeat-path",
        type=str,
        default=None,
        help="Optional JSON heartbeat file path for worker liveness",
    )
    return p.parse_args(argv)


def _write_worker_heartbeat(
    heartbeat_path: Path,
    *,
    processed: int,
    idle_loops: int,
    status: str,
    started_at: datetime,
    queue: RunQueuePort,
) -> None:
    payload = {
        "status": status,
        "processed": processed,
        "idle_loops": idle_loops,
        "started_at": started_at.isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        from nimbusware_orchestrator.fleet_worker import (
            collect_fleet_worker_metrics,
            fleet_redis_worker_enabled,
        )

        if fleet_redis_worker_enabled():
            payload["fleet_metrics"] = collect_fleet_worker_metrics(queue)
    except ImportError:
        pass
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = heartbeat_path.with_suffix(heartbeat_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    os.replace(tmp, heartbeat_path)


def main(argv: list[str] | None = None) -> int:
    ns = _args(argv)
    queue = get_run_queue()
    orch, notify_stop, notify_thread = build_worker_orchestrator()
    hb = Path(ns.heartbeat_path).expanduser() if ns.heartbeat_path else None
    try:
        run_worker_loop(
            queue,
            orch,
            max_tasks=ns.max_tasks,
            idle_sleep_seconds=max(float(ns.idle_sleep_seconds), 0.0),
            max_idle_loops=ns.max_idle_loops,
            heartbeat_path=hb,
        )
    finally:
        if notify_stop is not None:
            notify_stop.set()
        if notify_thread is not None:
            notify_thread.join(timeout=5.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
