from __future__ import annotations

from typing import Any
from uuid import UUID

from orchestrator.model_routing.audit import active_role_claims_from_events

WRITER_STAGE_TAXONOMY: dict[str, str] = {
    "implementation": "backend_writer",
    "test_writer": "test_writer",
    "frontend_writer": "frontend_writer",
    "plan": "planner",
}

_STAGE_FOR_AGENT_ROLE = {v: k for k, v in WRITER_STAGE_TAXONOMY.items()}


def stage_role_claims(role_claims: dict[str, str] | None) -> dict[str, str]:
    if not role_claims:
        return {}
    out: dict[str, str] = {}
    for key, claimer in role_claims.items():
        if key in WRITER_STAGE_TAXONOMY:
            out[key] = claimer
            continue
        stage = _STAGE_FOR_AGENT_ROLE.get(key)
        out[stage or key] = claimer
    return out


def role_claims_for_run(store: Any, run_id: UUID) -> dict[str, str]:
    rows = store.list_run_events(str(run_id))
    return active_role_claims_from_events(rows)


def node_capabilities_for_session(node_rows: list[Any]) -> dict[UUID, dict[str, Any]]:
    out: dict[UUID, dict[str, Any]] = {}
    for row in node_rows:
        caps = getattr(row, "capabilities", None)
        if isinstance(caps, dict):
            out[row.node_id] = dict(caps)
    return out


def optimizer_weights_from_session_metadata(metadata: dict[str, Any] | None) -> dict[str, float]:
    from orchestrator.collab.optimizer import (
        normalize_optimizer_weights,
        weights_from_priority,
    )

    meta = metadata if isinstance(metadata, dict) else {}
    raw_weights = meta.get("optimizer_weights")
    if isinstance(raw_weights, dict):
        return normalize_optimizer_weights({str(k): float(v) for k, v in raw_weights.items() if k})
    priority = meta.get("optimizer_priority")
    if isinstance(priority, list):
        return weights_from_priority([str(k) for k in priority])
    return normalize_optimizer_weights(None)


def user_id_from_broker_node(item: dict[str, Any]) -> str:
    from compute.broker_node_match import user_id_from_broker_node as _impl

    return _impl(item)


def caps_dict_from_broker_node(item: dict[str, Any]) -> dict[str, Any]:
    from compute.broker_node_match import caps_dict_from_broker_node as _impl

    return _impl(item)


def mesh_dispatch_context(
    store: Any,
    run_id: UUID,
    session_id: UUID,
) -> tuple[dict[str, str], dict[UUID, str], dict[UUID, dict[str, Any]], dict[str, float]]:
    from broker_client.flags import broker_compute_enabled
    from broker_client.stage_bind.compute import (
        build_compute_list_nodes_payload,
        compute_node_via_broker,
        node_id_from_broker_record,
    )
    from compute.node_store import build_compute_node_store
    from env.env_flags import nimbusware_database_url
    from maker.chat.session_store import build_chat_store

    role_claims = role_claims_for_run(store, run_id)
    chat_store = build_chat_store(nimbusware_database_url())
    sess = chat_store.get_session(session_id)
    opt_weights = optimizer_weights_from_session_metadata(
        sess.metadata if sess is not None else None,
    )

    if broker_compute_enabled():
        from compute.broker_session_status import assert_broker_compute_ok

        try:
            raw = assert_broker_compute_ok(
                compute_node_via_broker(
                    build_compute_list_nodes_payload(session_id=str(session_id))
                ),
                feature="mesh_dispatch_context",
                list_key="nodes",
            )
        except Exception as exc:  # noqa: BLE001
            # sak432-d / sak438-b: COMPUTE=1|2 miss is explicit (no silent empty maps).
            raise RuntimeError(f"broker_miss: mesh_dispatch_context: {exc}") from exc
        if isinstance(raw.get("nodes"), list):
            node_users: dict[UUID, str] = {}
            node_caps: dict[UUID, dict[str, Any]] = {}
            for item in raw["nodes"]:
                if not isinstance(item, dict):
                    continue
                nid_s = node_id_from_broker_record(item)
                if not nid_s:
                    continue
                try:
                    nid = UUID(nid_s)
                except ValueError:
                    continue
                uid = user_id_from_broker_node(item)
                if uid:
                    node_users[nid] = uid
                node_caps[nid] = caps_dict_from_broker_node(item)
            return role_claims, node_users, node_caps, opt_weights
        raise RuntimeError("broker_miss: mesh_dispatch_context: no nodes in broker response")

    rows = build_compute_node_store(nimbusware_database_url()).list_for_session(session_id)
    node_users = node_users_for_session(rows)
    node_caps = node_capabilities_for_session(rows)
    return role_claims, node_users, node_caps, opt_weights


def node_users_for_session(node_rows: list[Any]) -> dict[UUID, str]:
    out: dict[UUID, str] = {}
    for row in node_rows:
        uid = str(getattr(row, "user_id", "") or "")
        if uid:
            out[row.node_id] = uid
    return out
