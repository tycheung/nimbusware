"""Shared broker session compute status (nodes + queue depth) (`sak435-d` / `sak437-a` / `sak438-a` / `sak492-g`)."""

from __future__ import annotations

from typing import Any

from broker_client.peel_assert import (
    assert_broker_compute_ok,
    assert_broker_compute_record_ok,
    assert_capacity_ok,
    is_claim_empty_queue_error,
    is_compute_miss,
    normalize_claim_work_response,
)

__all__ = [
    "assert_broker_compute_ok",
    "assert_broker_compute_record_ok",
    "assert_capacity_ok",
    "broker_session_compute_status",
    "is_claim_empty_queue_error",
    "is_compute_miss",
    "normalize_claim_work_response",
]


def _broker_session_queue_miss(
    exc: BaseException,
    *,
    nodes: list[dict[str, Any]],
    session_id: str | None,
    feature: str | None,
) -> dict[str, Any]:
    """Nodes-ok + queue-fail → ``broker_miss``/degraded (never ``via=broker`` success)."""
    err = str(exc)
    if err.startswith("broker_miss:"):
        parts = err.split(":", 2)
        if len(parts) >= 3:
            err = parts[2].strip()
    out: dict[str, Any] = {
        "nodes": nodes,
        "queue_depth": 0,
        "via": "broker_miss",
        "status": "degraded",
        "error": err,
    }
    if session_id is not None:
        out["session_id"] = session_id
    if feature:
        out["feature"] = feature
    return out


def _broker_queue_depth_for_session(
    session_id: str | None,
    *,
    feature: str,
) -> int:
    """Queued depth via broker list; raises on peel miss (`sak492-g`)."""
    from broker_client.stage_bind.compute import (
        build_compute_list_payload,
        compute_work_via_broker,
        queue_depth_for_session,
    )

    work_raw = assert_broker_compute_ok(
        compute_work_via_broker(
            build_compute_list_payload(status="queued", limit=200)
        ),
        feature=f"{feature}.work",
        list_key="work",
    )
    items = [w for w in work_raw["work"] if isinstance(w, dict)]
    return queue_depth_for_session(items, session_id)


def broker_session_compute_status(
    session_id: str | None = None,
    *,
    feature: str | None = None,
) -> dict[str, Any]:
    """List broker nodes and queued work for a session.

    Node-list failure raises for caller ``broker_miss`` / HTTP 503 mapping.
    Queue-list failure after nodes succeed returns ``broker_miss`` + ``degraded``
    with nodes preserved — never ``via=broker`` with ``queue_depth=0`` (`sak492-g`).
    """
    from broker_client.stage_bind.compute import (
        build_compute_list_nodes_payload,
        compute_node_via_broker,
        node_id_from_broker_record,
    )

    feat = feature or "session_compute_status"
    nodes_raw = assert_broker_compute_ok(
        compute_node_via_broker(
            build_compute_list_nodes_payload(session_id=session_id)
        ),
        feature=f"{feat}.nodes",
        list_key="nodes",
    )
    nodes: list[dict[str, Any]] = []
    for item in nodes_raw.get("nodes") or []:
        if not isinstance(item, dict):
            continue
        nid = node_id_from_broker_record(item)
        nodes.append(
            {
                "node_id": nid,
                "display_name": item.get("label"),
                "host_label": item.get("label"),
                "status": "online",
                "capabilities": {
                    str(c): True for c in (item.get("caps") or []) if isinstance(c, str)
                },
                "session_id": item.get("session_id"),
                "via": "broker",
            }
        )

    try:
        queued = _broker_queue_depth_for_session(session_id, feature=feat)
    except Exception as exc:  # noqa: BLE001
        return _broker_session_queue_miss(
            exc,
            nodes=nodes,
            session_id=session_id,
            feature=feature,
        )

    out: dict[str, Any] = {
        "nodes": nodes,
        "queue_depth": queued,
        "via": "broker",
        "status": "ok",
    }
    if session_id is not None:
        out["session_id"] = session_id
    if feature:
        out["feature"] = feature
    return out
