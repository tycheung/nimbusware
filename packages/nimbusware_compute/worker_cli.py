from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from uuid import UUID

import httpx


def _register(
    client: httpx.Client,
    *,
    host_label: str,
    base_url: str,
    session_token: str,
) -> dict[str, Any]:
    headers: dict[str, str] = {}
    if session_token:
        headers["Authorization"] = f"Bearer {session_token}"
    resp = client.post(
        "/v1/compute/nodes/register",
        json={
            "host_label": host_label,
            "base_url": base_url,
            "display_name": host_label,
            "capabilities": {"stub": True},
        },
        headers=headers,
    )
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


def run_worker_loop(
    *,
    host_url: str,
    session_token: str,
    host_label: str,
    worker_base_url: str,
    interval_seconds: float,
    max_heartbeats: int | None,
) -> int:
    base = host_url.rstrip("/")
    with httpx.Client(base_url=base, timeout=30.0) as client:
        node = _register(
            client,
            host_label=host_label,
            base_url=worker_base_url,
            session_token=session_token,
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
            except httpx.HTTPError as exc:
                print(json.dumps({"heartbeat_error": str(exc)}), file=sys.stderr, flush=True)
            beats += 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Nimbusware compute mesh worker (register + heartbeat stub)",
    )
    parser.add_argument("--host-url", required=True, help="Host API base URL")
    parser.add_argument("--token", default="", help="Session compute token")
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
            interval_seconds=args.interval,
            max_heartbeats=max_beats,
        )
    except httpx.HTTPError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
