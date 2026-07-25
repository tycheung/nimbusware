from __future__ import annotations

import os
from typing import Any

from broker_client.client import BrokerClient
from broker_client.flags import broker_compute_enabled
from broker_client.mcp_client import BrokerMcpClient
from broker_client.stage_bind.llm import BrokerDisabled

_KNOWN_ACTIONS = frozenset({"enqueue", "claim", "complete", "get", "list", "requeue"})
_KNOWN_NODE_ACTIONS = frozenset({"register", "heartbeat", "list"})



def bind_compute_work(client: BrokerClient | None = None) -> dict[str, Any]:
    _ = client
    if not broker_compute_enabled():
        raise BrokerDisabled("NIMBUSWARE_BROKER_COMPUTE is not enabled")
    http_on = bool(os.environ.get("NIMBUSWARE_BROKER_HTTP", "").strip())
    return {
        "offer": "compute.work",
        "steps": ["provision", "bind", "invoke"],
        "transport": "http" if http_on else "mcp",
        "note": (
            "Prefer BrokerClient.compute_work() (HTTP POST /v1/sak/compute/work) when "
            "NIMBUSWARE_BROKER_HTTP is set; else BrokerMcpClient.call_tool('compute_work', ...)"
        ),
    }


def bind_compute_node(client: BrokerClient | None = None) -> dict[str, Any]:
    _ = client
    if not broker_compute_enabled():
        raise BrokerDisabled("NIMBUSWARE_BROKER_COMPUTE is not enabled")
    http_on = bool(os.environ.get("NIMBUSWARE_BROKER_HTTP", "").strip())
    return {
        "offer": "compute.node",
        "steps": ["provision", "bind", "invoke"],
        "transport": "http" if http_on else "mcp",
        "note": (
            "Prefer BrokerClient.compute_nodes() (HTTP POST /v1/sak/compute/nodes) when "
            "NIMBUSWARE_BROKER_HTTP is set; else BrokerMcpClient.call_tool('compute_node', ...)"
        ),
    }


def build_compute_enqueue_payload(
    kind: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "action": "enqueue",
        "kind": kind or "mesh_stage",
        "payload": dict(payload or {}),
    }


def build_compute_claim_payload(node_id: str) -> dict[str, Any]:
    return {"action": "claim", "node_id": node_id}


def build_compute_complete_payload(
    *,
    work_id: str,
    node_id: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "action": "complete",
        "work_id": work_id,
        "node_id": node_id,
        "result": dict(result),
    }


def build_compute_get_payload(work_id: str) -> dict[str, Any]:
    return {"action": "get", "work_id": work_id}


def build_compute_requeue_payload(work_id: str) -> dict[str, Any]:
    return {"action": "requeue", "work_id": work_id}


def work_session_id(work: dict[str, Any]) -> str:
    """Session id from broker work unit payload (`sak430-f`)."""
    payload = work.get("payload")
    if isinstance(payload, dict) and payload.get("session_id") is not None:
        return str(payload.get("session_id"))
    if work.get("session_id") is not None:
        return str(work.get("session_id"))
    return ""


def queue_depth_for_session(
    work_items: list[dict[str, Any]],
    session_id: str | None,
) -> int:
    """Count queued work; optionally filter by session_id (`sak430-f`)."""
    if not session_id:
        return len(work_items)
    return sum(1 for w in work_items if work_session_id(w) == session_id)


def terminate_restart_via_broker(
    work_id: str,
    *,
    client: BrokerMcpClient | None = None,
    http: BrokerClient | None = None,
) -> dict[str, Any]:
    """Requeue claimed work via broker (`sak430-e` / `sak439-b`)."""
    from compute.broker_session_status import assert_broker_compute_record_ok

    return assert_broker_compute_record_ok(  # sak484-i
        compute_work_via_broker(
            build_compute_requeue_payload(work_id),
            client=client,
            http=http,
        ),
        feature="terminate_restart_via_broker",
        record_key="work",
    )


def build_compute_list_payload(
    *,
    run_id: str | None = None,
    stage_name: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"action": "list"}
    if run_id:
        out["run_id"] = run_id
    if stage_name:
        out["stage_name"] = stage_name
    if status:
        out["status"] = status
    if limit is not None:
        out["limit"] = limit
    return out


def normalize_compute_work_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Ensure ``compute_work`` payloads carry a known ``action`` field.

    Mesh-style dicts without ``action`` are wrapped as an enqueue request.
    """
    action = payload.get("action")
    if isinstance(action, str) and action in _KNOWN_ACTIONS:
        return payload
    if isinstance(action, str) and action:
        return payload
    return build_compute_enqueue_payload(
        str(payload.get("stage_name") or payload.get("kind") or "mesh_stage"),
        payload,
    )


def compute_work_via_broker(
    payload: dict[str, Any],
    *,
    client: BrokerMcpClient | None = None,
    http: BrokerClient | None = None,
) -> dict[str, Any]:
    """Invoke ``compute_work`` — HTTP-first when ``NIMBUSWARE_BROKER_HTTP`` is set (`sak421-f`)."""
    if not broker_compute_enabled():
        raise BrokerDisabled(
            "Set NIMBUSWARE_BROKER_COMPUTE=1 or =2 to route compute through the broker"
        )
    normalized = normalize_compute_work_payload(payload)
    http_url = os.environ.get("NIMBUSWARE_BROKER_HTTP", "").strip()
    if http_url or http is not None:
        try:
            admin = http or BrokerClient()
            result = admin.compute_work(normalized)
            # sak438-a: never treat error+work/[] as success — return shape for assert.
            if isinstance(result, dict) and "error" not in result:
                return result
            return result if isinstance(result, dict) else {"result": result}
        except Exception:
            # sak436-a / sak491-f: HTTP transport failure re-raises (no MCP fallthrough).
            raise
    mcp = client or BrokerMcpClient()
    result = mcp.call_tool("compute_work", normalized)
    return result if isinstance(result, dict) else {"result": result}


def build_compute_register_payload(
    label: str,
    *,
    caps: list[str] | None = None,
    node_id: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"action": "register", "label": label or "worker"}
    if caps is not None:
        out["caps"] = list(caps)
    if node_id:
        out["node_id"] = node_id
    if session_id:
        out["session_id"] = session_id
    return out


def build_compute_heartbeat_payload(node_id: str) -> dict[str, Any]:
    return {"action": "heartbeat", "node_id": node_id}


def build_compute_list_nodes_payload(
    *,
    stale_secs: int | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"action": "list"}
    if stale_secs is not None:
        out["stale_secs"] = stale_secs
    if session_id:
        out["session_id"] = session_id
    return out


def normalize_compute_node_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Ensure ``compute_node`` payloads carry a known ``action`` field."""
    action = payload.get("action")
    if isinstance(action, str) and action in _KNOWN_NODE_ACTIONS:
        return payload
    if isinstance(action, str) and action:
        return payload
    return build_compute_register_payload(
        str(payload.get("label") or payload.get("host_label") or "worker"),
        caps=payload.get("caps") if isinstance(payload.get("caps"), list) else None,
        node_id=str(payload["node_id"]) if payload.get("node_id") else None,
    )


def node_id_from_broker_record(node: dict[str, Any] | None) -> str:
    """Extract node id from HTTP/MCP node records (``id`` or ``node_id``).

    Canonical impl: ``compute.broker_node_match.node_id_from_broker_record`` (`sak441-d`).
    """
    from compute.broker_node_match import node_id_from_broker_record as _impl

    return _impl(node)


def compute_node_via_broker(
    payload: dict[str, Any],
    *,
    client: BrokerMcpClient | None = None,
    http: BrokerClient | None = None,
) -> dict[str, Any]:
    """Invoke ``compute_node`` — HTTP-first when ``NIMBUSWARE_BROKER_HTTP`` is set (`sak422-b`)."""
    if not broker_compute_enabled():
        raise BrokerDisabled(
            "Set NIMBUSWARE_BROKER_COMPUTE=1 or =2 to route compute through the broker"
        )
    normalized = normalize_compute_node_payload(payload)
    http_url = os.environ.get("NIMBUSWARE_BROKER_HTTP", "").strip()
    if http_url or http is not None:
        try:
            admin = http or BrokerClient()
            result = admin.compute_nodes(normalized)
            # sak438-a: never treat error+nodes/[] as success — return shape for assert.
            if isinstance(result, dict) and "error" not in result:
                return result
            return result if isinstance(result, dict) else {"result": result}
        except Exception:
            # sak436-a / sak491-f: HTTP transport failure re-raises (no MCP fallthrough).
            raise
    mcp = client or BrokerMcpClient()
    result = mcp.call_tool("compute_node", normalized)
    if isinstance(result, dict):
        # MCP invoke often returns the NodeRecord / list body directly.
        if "node" not in result and "nodes" not in result and "id" in result:
            return {"node": result, "action": normalized.get("action"), "backend": "mcp"}
        return result
    return {"result": result}
