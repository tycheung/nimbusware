from __future__ import annotations

from typing import Any
from uuid import UUID

from nimbusware_orchestrator.model_binding_audit import active_role_claims_from_events

WRITER_STAGE_TAXONOMY: dict[str, str] = {
    "implementation": "backend_writer",
    "test_writer": "test_writer",
    "frontend_writer": "frontend_writer",
    "plan": "planner",
}

_STAGE_FOR_AGENT_ROLE = {v: k for k, v in WRITER_STAGE_TAXONOMY.items()}


def stage_role_claims(role_claims: dict[str, str] | None) -> dict[str, str]:
    """Map agent_role keys to pipeline stage names for mesh assignment."""
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


def node_users_for_session(node_rows: list[Any]) -> dict[UUID, str]:
    out: dict[UUID, str] = {}
    for row in node_rows:
        uid = str(getattr(row, "user_id", "") or "")
        if uid:
            out[row.node_id] = uid
    return out
