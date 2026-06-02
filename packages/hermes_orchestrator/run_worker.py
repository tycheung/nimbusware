"""Run-dispatch worker loop for queued verify tasks."""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from hermes_extensions.bundle_memory_factory import build_bundle_outcome_store
from hermes_memory.factory import build_memory_chunk_store
from hermes_orchestrator.pipeline import RunOrchestrator, default_paths
from hermes_orchestrator.registry import RoleRegistry
from hermes_orchestrator.run_dispatch import RunQueuePort, get_run_queue
from hermes_store.memory import InMemoryEventStore
from hermes_store.postgres import PostgresEventStore
from nimbusware_config import ConfigMaterializer, config_from_db_enabled


def build_worker_orchestrator() -> tuple[
    RunOrchestrator, threading.Event | None, threading.Thread | None
]:
    repo = Path(os.environ.get("NIMBUSWARE_REPO_ROOT", ".")).resolve()
    base, _ = default_paths(repo)
    url = os.environ.get("NIMBUSWARE_DATABASE_URL")
    use_db_config = config_from_db_enabled()
    materializer: ConfigMaterializer | None = None
    notify_stop: threading.Event | None = None
    notify_thread: threading.Thread | None = None
    if use_db_config and url:
        materializer = ConfigMaterializer(repo, use_db=True)
        registry = materializer.get_role_registry()
        from nimbusware_config import (
            config_notify_listener_enabled,
            get_config_notify_hub,
            start_config_notify_listener,
        )

        if config_notify_listener_enabled():
            hub = get_config_notify_hub()
            hub.register(materializer)
            notify_stop = threading.Event()
            notify_thread = start_config_notify_listener(url, hub, notify_stop)
    else:
        registry = RoleRegistry.from_yaml(repo / "configs" / "roles.yaml")
    if url:
        store = PostgresEventStore(url)
    else:
        store = InMemoryEventStore()
    orch = RunOrchestrator(
        store,
        registry,
        repo_root=repo,
        base_config_path=base,
        config_materializer=materializer,
        memory_chunk_store=build_memory_chunk_store(url),
        bundle_outcome_store=build_bundle_outcome_store(url),
    )
    return orch, notify_stop, notify_thread


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
        if str(task.step).strip().lower() != "verify":
            queue.ack(task.task_id)
            continue
        orchestrator.process_verify_dispatch_task(task)
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


def _args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Hermes agent run-dispatch worker")
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
        from hermes_orchestrator.fleet_worker import (
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
    _ = UUID  # keep pyright/mypy happy for import set parity with orchestrator typing
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
