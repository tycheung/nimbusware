from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from uuid import UUID

import httpx

from nimbusware_compute.work_unit import WorkUnitRecord
from nimbusware_compute.work_unit_execute import execute_work_unit_on_worker


def _register(
    client: httpx.Client,
    *,
    host_label: str,
    base_url: str,
    session_token: str,
    session_id: str,
    capabilities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers: dict[str, str] = {}
    if session_token:
        headers["Authorization"] = f"Bearer {session_token}"
    caps = {"mesh_worker": True}
    if capabilities:
        caps.update(capabilities)
    payload: dict[str, Any] = {
        "host_label": host_label,
        "base_url": base_url,
        "display_name": host_label,
        "capabilities": caps,
    }
    if session_id:
        payload["session_id"] = session_id
    resp = client.post("/v1/compute/nodes/register", json=payload, headers=headers)
    resp.raise_for_status()
    body = resp.json()
    node = body.get("node")
    if not isinstance(node, dict):
        msg = "register response missing node"
        raise RuntimeError(msg)
    return node


def _heartbeat(client: httpx.Client, node_id: str) -> dict[str, Any]:
    resp = client.post(
        f"/v1/compute/nodes/{node_id}/heartbeat",
        json={"status": "online"},
    )
    resp.raise_for_status()
    body = resp.json()
    node = body.get("node")
    if not isinstance(node, dict):
        msg = "heartbeat response missing node"
        raise RuntimeError(msg)
    return node


def _claim(
    client: httpx.Client,
    *,
    node_id: str,
    session_id: str,
) -> dict[str, Any] | None:
    body: dict[str, Any] = {"node_id": node_id}
    if session_id:
        body["session_id"] = session_id
    resp = client.post("/v1/compute/work-units/claim", json=body)
    resp.raise_for_status()
    data = resp.json()
    unit = data.get("work_unit")
    return unit if isinstance(unit, dict) else None


def _complete(
    client: httpx.Client,
    work_unit_id: str,
    *,
    status: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    resp = client.post(
        f"/v1/compute/work-units/{work_unit_id}/complete",
        json={"status": status, "result": result},
    )
    resp.raise_for_status()
    body = resp.json()
    unit = body.get("work_unit")
    if not isinstance(unit, dict):
        msg = "complete response missing work_unit"
        raise RuntimeError(msg)
    return unit


def _work_unit_record_from_public(raw: dict[str, Any]) -> WorkUnitRecord:
    return WorkUnitRecord(
        work_unit_id=UUID(str(raw["work_unit_id"])),
        run_id=UUID(str(raw["run_id"])),
        session_id=UUID(str(raw["session_id"])) if raw.get("session_id") else None,
        stage_name=str(raw.get("stage_name") or ""),
        agent_role=str(raw.get("agent_role") or ""),
        executor_user_id=str(raw.get("executor_user_id") or ""),
        status=str(raw.get("status") or "assigned"),
        payload=dict(raw.get("payload") or {}),
        node_id=UUID(str(raw["node_id"])) if raw.get("node_id") else None,
    )


def run_worker_loop(
    *,
    host_url: str,
    session_token: str,
    host_label: str,
    worker_base_url: str,
    session_id: str,
    interval_seconds: float,
    max_heartbeats: int | None,
    pull_work_units: bool,
    capabilities: dict[str, Any] | None = None,
) -> int:
    base = host_url.rstrip("/")
    with httpx.Client(base_url=base, timeout=30.0) as client:
        node = _register(
            client,
            host_label=host_label,
            base_url=worker_base_url,
            session_token=session_token,
            session_id=session_id,
            capabilities=capabilities,
        )
        node_id = str(node.get("node_id") or "")
        if not node_id:
            print(json.dumps({"error": "no node_id from register"}), file=sys.stderr)
            return 1
        print(json.dumps({"registered": node}), flush=True)
        beats = 0
        while max_heartbeats is None or beats < max_heartbeats:
            time.sleep(interval_seconds)
            try:
                updated = _heartbeat(client, node_id)
                print(json.dumps({"heartbeat": updated}), flush=True)
                if pull_work_units:
                    claimed = _claim(client, node_id=node_id, session_id=session_id)
                    if claimed is not None:
                        rec = _work_unit_record_from_public(claimed)
                        result = execute_work_unit_on_worker(rec)
                        completed = _complete(
                            client,
                            str(rec.work_unit_id),
                            status="ok" if result.get("ok") else "failed",
                            result=result,
                        )
                        print(json.dumps({"work_unit_completed": completed}), flush=True)
            except httpx.HTTPError as exc:
                print(json.dumps({"worker_error": str(exc)}), file=sys.stderr, flush=True)
            beats += 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Nimbusware compute mesh worker (register, heartbeat, work-unit pull)",
    )
    parser.add_argument("--host-url", required=True, help="Host API base URL")
    parser.add_argument("--token", default="", help="Session compute token")
    parser.add_argument("--session-id", default="", help="Collaborative session UUID")
    parser.add_argument(
        "--host-label",
        default="",
        help="Worker host label (default: machine hostname)",
    )
    parser.add_argument(
        "--worker-base-url",
        default="http://127.0.0.1:0",
        help="Callback reachability URL advertised to host",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="Heartbeat interval seconds",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Register and send one heartbeat then exit",
    )
    parser.add_argument(
        "--no-pull",
        action="store_true",
        help="Skip work-unit claim/complete loop (heartbeat only)",
    )
    args = parser.parse_args(argv)
    import socket

    label = args.host_label.strip() or socket.gethostname()
    max_beats = 1 if args.once else None
    try:
        return run_worker_loop(
            host_url=args.host_url,
            session_token=args.token,
            host_label=label,
            worker_base_url=args.worker_base_url,
            session_id=args.session_id.strip(),
            interval_seconds=args.interval,
            max_heartbeats=max_beats,
            pull_work_units=not args.no_pull,
        )
    except httpx.HTTPError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
