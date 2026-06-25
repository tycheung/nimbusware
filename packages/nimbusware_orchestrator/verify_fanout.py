from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from nimbusware_env.env_flags import nimbusware_redis_url, nimbusware_run_dispatch_mode
from nimbusware_orchestrator.run_dispatch import RunDispatchTask, get_run_queue
from nimbusware_orchestrator.verifiers import (
    VERIFIER_SHARD_NAMES,
    merge_verifier_shard_logs,
    run_writer_verifier_bundle,
    run_writer_verifier_shard,
)

_FANOUT_LOCK = threading.Lock()
_FANOUT_RESULTS: dict[str, dict[str, tuple[int, str]]] = {}


def verify_dispatch_fanout_enabled() -> bool:
    from nimbusware_env.env_flags import env_truthy_raw

    return (
        env_truthy_raw("NIMBUSWARE_VERIFY_DISPATCH_FANOUT")
        and nimbusware_run_dispatch_mode() is not None
    )


def _redis_client() -> Any | None:
    if nimbusware_run_dispatch_mode() != "redis":
        return None
    url = nimbusware_redis_url()
    if not url:
        return None
    try:
        import redis
    except ImportError:
        return None
    return redis.Redis.from_url(url, decode_responses=True)


def _fanout_key(fanout_id: str) -> str:
    return f"nimbusware:verify_fanout:{fanout_id}"


def record_verify_shard_result(fanout_id: str, shard: str, code: int, log: str) -> None:
    client = _redis_client()
    if client is not None:
        client.hset(
            _fanout_key(fanout_id),
            shard,
            json.dumps({"code": code, "log": log}, separators=(",", ":")),
        )
        return
    with _FANOUT_LOCK:
        bucket = _FANOUT_RESULTS.setdefault(fanout_id, {})
        bucket[shard] = (code, log)


def _fanout_shard_results(fanout_id: str) -> dict[str, tuple[int, str]]:
    client = _redis_client()
    if client is not None:
        raw = client.hgetall(_fanout_key(fanout_id))
        out: dict[str, tuple[int, str]] = {}
        for shard, payload in raw.items():
            try:
                data = json.loads(payload)
                out[str(shard)] = (int(data.get("code", 1)), str(data.get("log") or ""))
            except (TypeError, ValueError, json.JSONDecodeError):
                out[str(shard)] = (1, str(payload))
        return out
    with _FANOUT_LOCK:
        return dict(_FANOUT_RESULTS.get(fanout_id, {}))


def _fanout_complete(fanout_id: str) -> bool:
    return len(_fanout_shard_results(fanout_id)) >= len(VERIFIER_SHARD_NAMES)


def _clear_fanout(fanout_id: str) -> None:
    client = _redis_client()
    if client is not None:
        client.delete(_fanout_key(fanout_id))
        return
    with _FANOUT_LOCK:
        _FANOUT_RESULTS.pop(fanout_id, None)


def wait_verify_fanout(fanout_id: str, *, timeout_seconds: float = 300.0) -> bool:
    deadline = time.monotonic() + max(5.0, timeout_seconds)
    while time.monotonic() < deadline:
        if _fanout_complete(fanout_id):
            return True
        time.sleep(0.25)
    return _fanout_complete(fanout_id)


def merge_verify_fanout(fanout_id: str) -> tuple[int, str]:
    results = _fanout_shard_results(fanout_id)
    ordered = {
        name: results.get(name, (1, f"missing shard {name}")) for name in VERIFIER_SHARD_NAMES
    }
    code, log = merge_verifier_shard_logs(ordered)
    _clear_fanout(fanout_id)
    return code, log


def dispatch_verify_shards(run_id: str, workspace: Path) -> str | None:
    if not verify_dispatch_fanout_enabled():
        return None
    fanout_id = str(uuid4())
    queue = get_run_queue()
    ws = str(workspace.resolve())
    for shard in VERIFIER_SHARD_NAMES:
        queue.enqueue(
            RunDispatchTask(
                run_id=run_id,
                step="verify_shard",
                payload={"shard": shard, "fanout_id": fanout_id, "workspace": ws},
            ),
        )
    return fanout_id


def run_writer_verifier_resolved(
    workspace: Path,
    *,
    run_id: str | None = None,
    timeout_seconds: float = 300.0,
) -> tuple[int, str]:
    if run_id is None:
        return run_writer_verifier_bundle(workspace)
    fanout_id = dispatch_verify_shards(run_id, workspace)
    if fanout_id is None:
        return run_writer_verifier_bundle(workspace)
    if not wait_verify_fanout(fanout_id, timeout_seconds=timeout_seconds):
        _clear_fanout(fanout_id)
        return 1, "verify fan-out timed out waiting for worker shards"
    return merge_verify_fanout(fanout_id)


def process_verify_shard_task(task: RunDispatchTask) -> None:
    payload = dict(task.payload or {})
    shard = str(payload.get("shard") or "").strip().lower()
    fanout_id = str(payload.get("fanout_id") or "").strip()
    ws_raw = payload.get("workspace")
    if not shard or not fanout_id or not ws_raw:
        return
    code, log = run_writer_verifier_shard(Path(str(ws_raw)), shard)
    record_verify_shard_result(fanout_id, shard, code, log)
