from __future__ import annotations

from typing import Any

from agent_core.models import EventType
from nimbusware_store.protocol import serialized_event_from_row

_BINDING_EVENT_TYPES = frozenset(
    {
        EventType.MODEL_BINDING_OVERRIDDEN.value,
        EventType.WORKLOAD_ROLE_CLAIMED.value,
        EventType.WORKLOAD_ROLE_RELEASED.value,
    },
)


def active_role_claims_from_events(rows: list[dict[str, Any]]) -> dict[str, str]:
    claims: dict[str, str] = {}
    for row in rows:
        et = str(row.get("event_type") or "")
        ev = serialized_event_from_row(row)
        payload = ev.get("payload") if isinstance(ev, dict) else {}
        if not isinstance(payload, dict):
            continue
        role = str(payload.get("agent_role") or "")
        if not role:
            continue
        if et == EventType.WORKLOAD_ROLE_CLAIMED.value:
            claims[role] = str(payload.get("claimer_user_id") or "")
        elif et == EventType.WORKLOAD_ROLE_RELEASED.value:
            claims.pop(role, None)
    return claims


def extract_model_binding_audit_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        et = str(row.get("event_type") or "")
        if et not in _BINDING_EVENT_TYPES:
            continue
        ev = serialized_event_from_row(row)
        payload = ev.get("payload") if isinstance(ev, dict) else {}
        out.append(
            {
                "event_type": et,
                "event_id": str(row.get("event_id") or ""),
                "occurred_at": str(row.get("occurred_at") or ""),
                "payload": payload if isinstance(payload, dict) else {},
            },
        )
    return out
