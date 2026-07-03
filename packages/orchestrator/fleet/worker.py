from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, cast

from agent_core.mapping import mapping_or_empty
from env.env_flags import nimbusware_redis_url, nimbusware_repo_root_path
from env.settings_resolve import resolve_int
from orchestrator.run_dispatch import RunQueuePort, run_dispatch_mode

BackpressureLevel = Literal["ok", "warn", "critical", "unknown"]


def fleet_redis_worker_enabled() -> bool:
    if run_dispatch_mode() != "redis":
        return False
    if not nimbusware_redis_url():
        return False
    try:
        from env.edition import enterprise_feature_enabled

        return enterprise_feature_enabled("redis_fleet_worker")
    except ImportError:
        return False


def fleet_queue_backpressure_limits() -> tuple[int, int]:
    pending_max = max(1, resolve_int("NIMBUSWARE_FLEET_QUEUE_BACKPRESSURE_DEPTH", default=100))
    inflight_max = max(1, resolve_int("NIMBUSWARE_FLEET_QUEUE_BACKPRESSURE_IN_FLIGHT", default=20))
    return pending_max, inflight_max


def queue_stats(queue: RunQueuePort) -> dict[str, int]:
    stats_fn = getattr(queue, "stats", None)
    if callable(stats_fn):
        raw = stats_fn()
        if isinstance(raw, dict):
            return {
                "pending": int(raw.get("pending", 0)),
                "in_flight": int(raw.get("in_flight", 0)),
            }
    return {"pending": 0, "in_flight": 0}


def evaluate_backpressure(*, pending: int, in_flight: int) -> BackpressureLevel:
    pending_max, inflight_max = fleet_queue_backpressure_limits()
    if pending >= pending_max * 2 or in_flight >= inflight_max * 2:
        return "critical"
    if pending >= pending_max or in_flight >= inflight_max:
        return "warn"
    return "ok"


def collect_fleet_worker_metrics(queue: RunQueuePort | None = None) -> dict[str, Any]:
    """Queue depth + back-pressure snapshot for health endpoints and worker heartbeat."""
    from orchestrator.run_dispatch import get_run_queue

    q = queue or get_run_queue()
    stats = queue_stats(q)
    pending = stats["pending"]
    inflight = stats["in_flight"]
    pending_max, inflight_max = fleet_queue_backpressure_limits()
    level = evaluate_backpressure(pending=pending, in_flight=inflight)
    return {
        "dispatch_mode": run_dispatch_mode(),
        "pending": pending,
        "in_flight": inflight,
        "backpressure": level,
        "limits": {
            "pending_warn": pending_max,
            "in_flight_warn": inflight_max,
        },
        "fleet_profile_enabled": fleet_redis_worker_enabled(),
    }


def read_worker_heartbeat(path: Path | str | None = None) -> dict[str, Any] | None:
    if path is None:
        repo = nimbusware_repo_root_path()
        path = repo / ".cache" / "run_dispatch_worker_heartbeat.json"
    hb_path = Path(path)
    if not hb_path.is_file():
        return None
    try:
        return cast(dict[str, Any], json.loads(hb_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return None


def fleet_worker_health_snapshot(*, heartbeat_path: Path | str | None = None) -> dict[str, Any]:
    """Aggregate Redis queue metrics + optional on-disk worker heartbeat."""
    metrics: dict[str, Any] = {
        "fleet_profile_enabled": fleet_redis_worker_enabled(),
        "dispatch_mode": run_dispatch_mode(),
        "redis_url_configured": bool(nimbusware_redis_url()),
    }
    if fleet_redis_worker_enabled():
        try:
            metrics["queue"] = collect_fleet_worker_metrics()
        except Exception as exc:
            metrics["queue"] = {"error": str(exc)[:200], "backpressure": "unknown"}
    hb = read_worker_heartbeat(heartbeat_path)
    if hb is not None:
        metrics["worker_heartbeat"] = hb
    queue_info = mapping_or_empty(metrics.get("queue"))
    backpressure = queue_info.get("backpressure", "unknown")
    return {
        "ok": backpressure in ("ok", "warn") and metrics.get("dispatch_mode") == "redis",
        "backpressure": backpressure,
        "metrics": metrics,
    }
