"""Map SwissArmyNoife compute.node / compute.work records to Nimbusware public shapes (`sak426`)."""

from __future__ import annotations

from typing import Any
from uuid import UUID


def caps_from_capabilities(capabilities: dict[str, Any] | None) -> list[str]:
    if not capabilities:
        return []
    out: list[str] = []
    for key, val in capabilities.items():
        if val is True or val == 1 or val == "true":
            out.append(str(key))
        elif isinstance(val, str) and val:
            out.append(f"{key}={val}")
        else:
            out.append(str(key))
    return out


def broker_node_public(
    item: dict[str, Any],
    *,
    session_id: UUID | None = None,
) -> dict[str, Any]:
    from broker_client.stage_bind.compute import node_id_from_broker_record

    caps = item.get("caps") if isinstance(item.get("caps"), list) else []
    cap_map = {str(c): True for c in caps if isinstance(c, str)}
    allow = any(
        str(c).startswith("allow_host_resource_management=true") for c in caps if isinstance(c, str)
    )
    sid = item.get("session_id") or (str(session_id) if session_id else None)
    return {
        "node_id": node_id_from_broker_record(item),
        "tenant_id": None,
        "session_id": sid,
        "user_id": "",
        "display_name": item.get("label"),
        "host_label": item.get("label"),
        "base_url": "",
        "capabilities": cap_map,
        "share_policy": "off",
        "allow_host_resource_management": allow,
        "last_heartbeat_at": None,
        "status": "online",
        "created_at": None,
        "via": "broker",
    }


def broker_work_public(work: dict[str, Any]) -> dict[str, Any]:
    payload = work.get("payload") if isinstance(work.get("payload"), dict) else {}
    status = str(work.get("status") or "queued")
    mapped = {
        "queued": "queued",
        "claimed": "assigned",
        "completed": "ok",
        "failed": "failed",
    }.get(status, status)
    return {
        "work_unit_id": str(work.get("id") or work.get("work_id") or ""),
        "run_id": payload.get("run_id"),
        "session_id": payload.get("session_id"),
        "node_id": str(work.get("claimed_by") or work.get("node_id") or "") or None,
        "stage_name": str(work.get("kind") or payload.get("stage_name") or ""),
        "agent_role": str(payload.get("agent_role") or work.get("kind") or ""),
        "executor_user_id": "",
        "status": mapped,
        "payload": payload,
        "result": work.get("result"),
        "assigned_at": None,
        "completed_at": None,
        "created_at": None,
        "via": "broker",
    }
