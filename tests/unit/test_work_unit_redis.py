from __future__ import annotations

from uuid import uuid4

import pytest

from nimbusware_compute.work_unit import get_work_unit_queue, set_work_unit_queue
from nimbusware_compute.work_unit_redis import RedisWorkUnitQueue


class _FakeRedis:
    def __init__(self) -> None:
        self.pending: list[str] = []
        self.records: dict[str, str] = {}

    def lpush(self, _key: str, value: str) -> None:
        self.pending.insert(0, value)

    def brpop(self, _key: str, timeout: int = 1) -> tuple[str, str] | None:
        _ = timeout
        if not self.pending:
            return None
        return ("queue", self.pending.pop())

    def lrange(self, _key: str, start: int, end: int) -> list[str]:
        _ = start, end
        return list(self.pending)

    def llen(self, _key: str) -> int:
        return len(self.pending)

    def hset(self, _key: str, field: str, value: str) -> None:
        self.records[field] = value

    def hget(self, _key: str, field: str) -> str | None:
        return self.records.get(field)

    def hgetall(self, _key: str) -> dict[str, str]:
        return dict(self.records)

    def hlen(self, _key: str) -> int:
        return len(self.records)


def test_redis_work_unit_queue_round_trip() -> None:
    fake = _FakeRedis()
    queue = RedisWorkUnitQueue("redis://example", client=fake)
    run_id = uuid4()
    session_id = uuid4()
    node_id = uuid4()
    enqueued = queue.enqueue(
        run_id=run_id,
        stage_name="implementation",
        session_id=session_id,
        payload={"mesh_assignment": True, "workspace": "."},
    )
    assert queue.queued_count() == 1
    assert queue.queued_count(session_id=session_id) == 1
    claimed = queue.dequeue(session_id=session_id, node_id=node_id)
    assert claimed is not None
    assert claimed.work_unit_id == enqueued.work_unit_id
    assert claimed.status == "assigned"
    assert claimed.node_id == node_id
    done = queue.complete(claimed.work_unit_id, status="ok", result={"ok": True})
    assert done is not None
    assert done.status == "ok"
    assert queue.queued_count() == 0


def test_get_work_unit_queue_redis_requires_url(monkeypatch: pytest.MonkeyPatch) -> None:
    set_work_unit_queue(None)
    monkeypatch.setenv("NIMBUSWARE_COMPUTE_WORK_QUEUE", "redis")
    monkeypatch.delenv("NIMBUSWARE_REDIS_URL", raising=False)
    with pytest.raises(ValueError, match="NIMBUSWARE_REDIS_URL"):
        get_work_unit_queue()
