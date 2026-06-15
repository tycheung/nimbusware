from __future__ import annotations

import json
import threading
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import uuid4

from nimbusware_env.env_flags import nimbusware_redis_url, nimbusware_run_dispatch_mode


@dataclass(frozen=True)
class RunDispatchTask:
    run_id: str
    step: str
    payload: dict[str, Any] = field(default_factory=dict)
    task_id: str = field(default_factory=lambda: str(uuid4()))


class RunQueuePort(Protocol):
    def enqueue(self, task: RunDispatchTask) -> None: ...

    def dequeue(self) -> RunDispatchTask | None: ...

    def ack(self, task_id: str) -> bool: ...


class InMemoryRunQueue:
    """Thread-safe FIFO queue for dev/tests (default when dispatch enabled)."""

    def __init__(self) -> None:
        self._pending: deque[RunDispatchTask] = deque()
        self._in_flight: dict[str, RunDispatchTask] = {}
        self._acked: set[str] = set()
        self._lock = threading.Lock()

    def enqueue(self, task: RunDispatchTask) -> None:
        with self._lock:
            self._pending.append(task)

    def dequeue(self) -> RunDispatchTask | None:
        with self._lock:
            if not self._pending:
                return None
            task = self._pending.popleft()
            self._in_flight[task.task_id] = task
            return task

    def ack(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._acked:
                return True
            task = self._in_flight.pop(task_id, None)
            if task is None:
                return False
            self._acked.add(task_id)
            return True

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "pending": len(self._pending),
                "in_flight": len(self._in_flight),
            }


class RedisRunQueue:
    """Redis-backed queue with in-flight task tracking."""

    def __init__(
        self,
        redis_url: str,
        *,
        queue_key: str = "nimbusware:run_dispatch:queue",
        in_flight_key: str = "nimbusware:run_dispatch:in_flight",
        client: Any | None = None,
    ) -> None:
        self._redis_url = redis_url
        self._queue_key = queue_key
        self._in_flight_key = in_flight_key
        if client is not None:
            self._client = client
            return
        try:
            import redis
        except ImportError as exc:
            msg = "redis package is required for NIMBUSWARE_RUN_DISPATCH=redis"
            raise RuntimeError(msg) from exc
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    @staticmethod
    def _serialize_task(task: RunDispatchTask) -> str:
        return json.dumps(
            {
                "task_id": task.task_id,
                "run_id": task.run_id,
                "step": task.step,
                "payload": task.payload,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    @staticmethod
    def _deserialize_task(raw: str) -> RunDispatchTask:
        data = json.loads(raw)
        return RunDispatchTask(
            run_id=str(data["run_id"]),
            step=str(data["step"]),
            payload=dict(data.get("payload") or {}),
            task_id=str(data["task_id"]),
        )

    def enqueue(self, task: RunDispatchTask) -> None:
        payload = self._serialize_task(task)
        # LPUSH + BRPOP gives FIFO semantics.
        self._client.lpush(self._queue_key, payload)

    def dequeue(self) -> RunDispatchTask | None:
        item = self._client.brpop(self._queue_key, timeout=1)
        if item is None:
            return None
        raw = item[1] if isinstance(item, tuple) else item
        if not isinstance(raw, str):
            raw = raw.decode() if isinstance(raw, bytes) else str(raw)
        task = self._deserialize_task(raw)
        self._client.hset(self._in_flight_key, task.task_id, raw)
        return task

    def ack(self, task_id: str) -> bool:
        if task_id in ("", None):
            return False
        removed = self._client.hdel(self._in_flight_key, str(task_id))
        return bool(removed)

    def stats(self) -> dict[str, int]:
        pending = int(self._client.llen(self._queue_key))
        in_flight = int(self._client.hlen(self._in_flight_key))
        return {"pending": pending, "in_flight": in_flight}


_GLOBAL_QUEUE: RunQueuePort | None = None
_GLOBAL_QUEUE_LOCK = threading.Lock()


def run_dispatch_mode() -> str | None:
    return nimbusware_run_dispatch_mode()


def run_dispatch_enabled() -> bool:
    return run_dispatch_mode() is not None


def get_run_queue() -> RunQueuePort:
    global _GLOBAL_QUEUE
    with _GLOBAL_QUEUE_LOCK:
        if _GLOBAL_QUEUE is not None:
            return _GLOBAL_QUEUE
    mode = run_dispatch_mode()
    if mode == "redis":
        url = nimbusware_redis_url()
        if not url:
            msg = "NIMBUSWARE_REDIS_URL required when NIMBUSWARE_RUN_DISPATCH=redis"
            raise ValueError(msg)
        return RedisRunQueue(url)
    with _GLOBAL_QUEUE_LOCK:
        if _GLOBAL_QUEUE is None:
            _GLOBAL_QUEUE = InMemoryRunQueue()
        return _GLOBAL_QUEUE


def set_run_queue(queue: RunQueuePort | None) -> None:
    """Test hook to inject a queue instance."""
    global _GLOBAL_QUEUE
    with _GLOBAL_QUEUE_LOCK:
        if queue is None:
            _GLOBAL_QUEUE = None
        elif isinstance(queue, InMemoryRunQueue):
            _GLOBAL_QUEUE = queue
        else:
            _GLOBAL_QUEUE = queue


def task_payload_workspace(payload: Mapping[str, Any] | None) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    raw = payload.get("workspace")
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None
