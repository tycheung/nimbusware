"""Enterprise Redis fleet worker."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from nimbusware_env.edition import DEFAULT_EDITION, ENTERPRISE_EDITION, ENV_EDITION
from nimbusware_orchestrator.fleet_worker import (
    collect_fleet_worker_metrics,
    evaluate_backpressure,
    fleet_redis_worker_enabled,
    read_worker_heartbeat,
)
from nimbusware_orchestrator.run_dispatch import InMemoryRunQueue, RedisRunQueue, RunDispatchTask


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


def test_evaluate_backpressure_levels() -> None:
    assert evaluate_backpressure(pending=0, in_flight=0) == "ok"
    assert evaluate_backpressure(pending=100, in_flight=0) == "warn"
    assert evaluate_backpressure(pending=250, in_flight=0) == "critical"


def test_in_memory_queue_stats() -> None:
    q = InMemoryRunQueue()
    q.enqueue(RunDispatchTask(run_id=str(uuid4()), step="verify"))
    stats = q.stats()
    assert stats["pending"] == 1
    assert stats["in_flight"] == 0


def test_redis_queue_stats() -> None:
    fake = _FakeRedis()
    q = RedisRunQueue("redis://example", client=fake)
    q.enqueue(RunDispatchTask(run_id=str(uuid4()), step="verify"))
    stats = q.stats()
    assert stats["pending"] == 1


def test_fleet_worker_disabled_on_individual(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, DEFAULT_EDITION)
    monkeypatch.setenv("NIMBUSWARE_RUN_DISPATCH", "redis")
    monkeypatch.setenv("NIMBUSWARE_REDIS_URL", "redis://127.0.0.1:6379/0")
    assert not fleet_redis_worker_enabled()


def test_fleet_metrics_with_memory_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_RUN_DISPATCH", "memory")
    assert not fleet_redis_worker_enabled()


def test_fleet_metrics_redis_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_RUN_DISPATCH", "redis")
    monkeypatch.setenv("NIMBUSWARE_REDIS_URL", "redis://127.0.0.1:6379/0")
    fake = _FakeRedis()
    q = RedisRunQueue("redis://example", client=fake)
    q.enqueue(RunDispatchTask(run_id=str(uuid4()), step="verify"))
    metrics = collect_fleet_worker_metrics(q)
    assert metrics["fleet_profile_enabled"] is True
    assert metrics["pending"] == 1
    assert metrics["backpressure"] in ("ok", "warn", "critical")


def test_read_worker_heartbeat(tmp_path: Path) -> None:
    hb = tmp_path / "hb.json"
    hb.write_text(json.dumps({"status": "idle", "processed": 0}), encoding="utf-8")
    payload = read_worker_heartbeat(hb)
    assert payload is not None
    assert payload["status"] == "idle"


def test_enterprise_fleet_worker_health_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_RUN_DISPATCH", "redis")
    monkeypatch.setenv("NIMBUSWARE_REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "test-admin-secret")
    from fastapi.testclient import TestClient

    from nimbusware_api.app import app
    from nimbusware_iam.constants import API_KEY_HEADER
    from nimbusware_orchestrator.run_dispatch import set_run_queue

    set_run_queue(RedisRunQueue("redis://example", client=_FakeRedis()))
    with TestClient(app) as client:
        boot = client.post(
            "/v1/enterprise/iam/bootstrap",
            headers={"X-Nimbusware-Admin-Token": "test-admin-secret"},
        )
        headers = {API_KEY_HEADER: boot.json()["api_key"]}
        r = client.get("/v1/enterprise/fleet-worker/health", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert "backpressure" in body
        assert "metrics" in body


def test_worker_heartbeat_includes_fleet_metrics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_RUN_DISPATCH", "redis")
    monkeypatch.setenv("NIMBUSWARE_REDIS_URL", "redis://127.0.0.1:6379/0")
    from datetime import datetime, timezone

    from nimbusware_orchestrator.run_worker import _write_worker_heartbeat

    fake = _FakeRedis()
    q = RedisRunQueue("redis://example", client=fake)
    hb = tmp_path / "hb.json"
    _write_worker_heartbeat(
        hb,
        processed=0,
        idle_loops=1,
        status="idle",
        started_at=datetime.now(timezone.utc),
        queue=q,
    )
    payload = json.loads(hb.read_text(encoding="utf-8"))
    assert "fleet_metrics" in payload
    assert payload["fleet_metrics"]["fleet_profile_enabled"] is True
