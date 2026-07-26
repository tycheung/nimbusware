from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from uuid import UUID

import httpx

from compute.work_unit import WorkUnitRecord
from compute.work_unit_execute import execute_work_unit_on_worker


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


def _broker_payload_from_work_unit(rec: WorkUnitRecord) -> dict[str, Any]:
    from broker_client.stage_bind.compute import build_compute_enqueue_payload

    nested: dict[str, Any] = {
        "work_unit_id": str(rec.work_unit_id),
        "run_id": str(rec.run_id),
        "stage_name": rec.stage_name,
        "agent_role": rec.agent_role,
        "executor_user_id": rec.executor_user_id,
        "payload": dict(rec.payload),
    }
    if rec.session_id is not None:
        nested["session_id"] = str(rec.session_id)
    if rec.node_id is not None:
        nested["node_id"] = str(rec.node_id)
    return build_compute_enqueue_payload(rec.stage_name or "mesh_stage", nested)


def execute_claimed_work_unit(rec: WorkUnitRecord) -> dict[str, Any]:
    """Try broker compute dual-run; under COMPUTE=1|2 do not fall back to local (`sak431-d`)."""
    from broker_client.flags import broker_compute_enabled
    from orchestrator import try_broker_compute_work

    result = try_broker_compute_work(_broker_payload_from_work_unit(rec))
    if result is not None:
        return result
    if broker_compute_enabled():
        raise RuntimeError(
            "broker_miss: execute_claimed_work_unit under NIMBUSWARE_BROKER_COMPUTE=1|2"
        )
    return execute_work_unit_on_worker(rec)


def _node_dict_from_broker_raw(
    raw: dict[str, Any],
    *,
    fallback_node_id: str = "",
    require_id: bool = False,
) -> dict[str, Any]:
    """Unwrap BrokerClient node responses (`sak440-e`)."""
    from broker_client.stage_bind.compute import node_id_from_broker_record

    node = raw.get("node") if isinstance(raw.get("node"), dict) else raw
    out = dict(node) if isinstance(node, dict) else {}
    node_id = node_id_from_broker_record(out) or fallback_node_id
    if require_id and not node_id:
        raise RuntimeError("broker_miss: register response missing node id")
    if node_id:
        out["node_id"] = node_id
    return out


def _stderr_broker_miss(exc: BaseException) -> None:
    print(
        json.dumps({"error": str(exc), "via": "broker_miss"}),
        file=sys.stderr,
        flush=True,
    )


def _broker_claim_work_or_miss(claimed: Any) -> dict[str, Any] | None:
    from broker_client.peel_assert import is_claim_empty_queue_error

    if not isinstance(claimed, dict):
        raise RuntimeError(f"broker_miss: claim response non-dict: {claimed!r}")
    if claimed.get("via") == "broker_miss" or claimed.get("status") == "degraded":
        raise RuntimeError(
            f"broker_miss: claim transport miss: "
            f"{claimed.get('error') or claimed.get('feature') or claimed!r}"
        )
    work = claimed.get("work")
    if work is None:
        if is_claim_empty_queue_error(claimed) or claimed.get("via") == "broker":
            return None
        raise RuntimeError(f"broker_miss: claim empty work without poll semantics: {claimed!r}")
    if not isinstance(work, dict):
        raise RuntimeError(f"broker_miss: claim work not a record: {work!r}")
    work_id = str(work.get("id") or work.get("work_id") or "")
    if not work_id:
        raise RuntimeError(f"broker_miss: claim work record missing id: {work!r}")
    return work


def _broker_register_node(
    *,
    host_label: str,
    capabilities: dict[str, Any] | None = None,
    session_id: str = "",
) -> dict[str, Any]:
    """Register via compute_node_via_broker (`sak422-b` / `sak434-c` / `sak439-a`)."""
    from broker_client.stage_bind.compute import (
        build_compute_register_payload,
        compute_node_via_broker,
    )

    caps = ["mesh_worker"]
    if capabilities:
        caps.extend(str(k) for k, v in capabilities.items() if v)
    raw = compute_node_via_broker(
        build_compute_register_payload(
            host_label,
            caps=caps,
            session_id=session_id or None,
        )
    )
    return _node_dict_from_broker_raw(raw, require_id=True)


def _broker_heartbeat_node(node_id: str) -> dict[str, Any]:
    """Heartbeat via compute_node_via_broker (`sak422-b` / `sak434-c` / `sak439-a`)."""
    from broker_client.stage_bind.compute import (
        build_compute_heartbeat_payload,
        compute_node_via_broker,
    )

    return _node_dict_from_broker_raw(
        compute_node_via_broker(build_compute_heartbeat_payload(node_id)),
        fallback_node_id=node_id,
    )


def _broker_claim_execute_complete(node_id: str) -> bool:
    """Claim → execute → complete via BrokerClient (`sak433-h` / `sak439-a` / `sak440-e`).

    Returns True when a work unit was claimed (even if complete fails).
    """
    from broker_client.client import BrokerClient
    from broker_client.flags import broker_compute_enabled
    from orchestrator import try_broker_compute_work

    client = BrokerClient()
    claimed = client.claim_work(node_id)
    work = _broker_claim_work_or_miss(claimed)  # sak490-a
    if work is None:
        return False
    work_id = str(work.get("id") or work.get("work_id") or "")
    kind = str(work.get("kind") or "mesh_stage")
    payload = work.get("payload") if isinstance(work.get("payload"), dict) else {}
    result = try_broker_compute_work(
        {
            "stage_name": kind,
            "kind": kind,
            "payload": payload,
            "work_unit_id": work_id,
            "node_id": node_id,
        }
    )
    if result is None and broker_compute_enabled():
        raise RuntimeError(
            f"broker_miss: execute returned None for work_id={work_id} under "
            "NIMBUSWARE_BROKER_COMPUTE=1|2"
        )
    if result is None:
        result = {"ok": True, "via": "broker_claim", "work_id": work_id}
    done = client.complete_work(
        work_id=work_id,
        node_id=node_id,
        result=result if isinstance(result, dict) else {"result": result},
    )
    print(json.dumps({"broker_work_unit_completed": done}), flush=True)
    return True


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
    from broker_client.flags import broker_compute_enabled, broker_compute_only

    def _is_broker_miss(exc: BaseException) -> bool:
        msg = str(exc).lower()
        return "broker_miss" in msg or "unavailable under nimbusware_broker_compute" in msg

    # sak433-h: broker-exclusive whenever COMPUTE is on (no local HTTP fallthrough).
    if broker_compute_only():
        try:
            node = _broker_register_node(
                host_label=host_label,
                capabilities=capabilities,
                session_id=session_id,
            )
        except Exception as exc:  # noqa: BLE001 — surface register failure
            if _is_broker_miss(exc):
                _stderr_broker_miss(exc)  # sak490-a
            else:
                print(json.dumps({"error": f"broker register: {exc}"}), file=sys.stderr)
            return 1
        node_id = str(node.get("node_id") or "")
        if not node_id:
            print(
                json.dumps({"error": "no node_id from broker register", "via": "broker_miss"}),
                file=sys.stderr,
            )
            return 1
        print(json.dumps({"registered": node, "via": "broker"}), flush=True)
        beats = 0
        while max_heartbeats is None or beats < max_heartbeats:
            time.sleep(interval_seconds)
            try:
                updated = _broker_heartbeat_node(node_id)
                print(json.dumps({"heartbeat": updated, "via": "broker"}), flush=True)
                if pull_work_units:
                    _broker_claim_execute_complete(node_id)
            except Exception as exc:  # noqa: BLE001 — sak441-b: peel miss exits
                if _is_broker_miss(exc):
                    _stderr_broker_miss(exc)  # sak490-a
                    return 1
                print(json.dumps({"worker_error": str(exc)}), file=sys.stderr, flush=True)
            beats += 1
        return 0

    if broker_compute_enabled():
        try:
            node = _broker_register_node(
                host_label=host_label,
                capabilities=capabilities,
                session_id=session_id,
            )
            node_id = str(node.get("node_id") or "")
            if node_id:
                print(json.dumps({"registered": node, "via": "broker"}), flush=True)
                beats = 0
                while max_heartbeats is None or beats < max_heartbeats:
                    time.sleep(interval_seconds)
                    try:
                        updated = _broker_heartbeat_node(node_id)
                        print(json.dumps({"heartbeat": updated, "via": "broker"}), flush=True)
                        if pull_work_units:
                            _broker_claim_execute_complete(node_id)
                    except Exception as exc:  # noqa: BLE001 — sak441-b
                        if _is_broker_miss(exc):
                            _stderr_broker_miss(exc)  # sak490-a
                            return 1
                        print(json.dumps({"worker_error": str(exc)}), file=sys.stderr, flush=True)
                    beats += 1
                return 0
            print(
                json.dumps({"error": "no node_id from broker register", "via": "broker_miss"}),
                file=sys.stderr,
            )
            return 1
        except Exception as exc:  # noqa: BLE001 — sak431-d: no local HTTP fallthrough
            _stderr_broker_miss(exc)  # sak490-a
            return 1

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
                        result = execute_claimed_work_unit(rec)
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
