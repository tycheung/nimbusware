"""BFF endpoints for Admin Preact UI (operator chat, formatted tables)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from agent_core.models import serialize_event_persistent, validate_event_dict
from hermes_store.protocol import serialized_event_from_row
from nimbusware_api.admin import AdminDep
from nimbusware_api.deps import StoreDep
from nimbusware_api.errors import problem
from nimbusware_api.schemas.openapi import PROBLEM_RESPONSE_404
from nimbusware_console.critic_matrix_display import critic_matrix_rows_from_events
from nimbusware_console.findings_display import findings_list_from_response, findings_table_rows
from nimbusware_console.operator_chat_core import ChatState, process_user_message

router = APIRouter(prefix="/admin/ui", tags=["admin-ui"])

_chat_sessions: dict[str, ChatState] = {}


class OperatorChatMessageBody(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


class OperatorChatMessageResponse(BaseModel):
    reply: str
    last_run_id: str = ""


@router.post("/operator-chat/message", response_model=OperatorChatMessageResponse)
def operator_chat_message(
    body: OperatorChatMessageBody,
    _admin: AdminDep,
    x_nimbusware_chat_session: str | None = Header(default=None),
) -> OperatorChatMessageResponse:
    key = (x_nimbusware_chat_session or "default").strip()[:128] or "default"
    state = _chat_sessions.setdefault(key, ChatState())
    reply = process_user_message(body.text, state)
    return OperatorChatMessageResponse(reply=reply, last_run_id=state.last_run_id)


@router.get(
    "/runs/{run_id}/findings-table",
    responses={404: PROBLEM_RESPONSE_404},
)
def findings_table(run_id: UUID, store: StoreDep, _admin: AdminDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    findings_raw: list[dict[str, Any]] = []
    for r in rows:
        if r["event_type"] != "finding.created":
            continue
        d = serialized_event_from_row(r)
        ev = validate_event_dict(d)
        findings_raw.append(serialize_event_persistent(ev))
    body = {"run_id": str(run_id), "findings": findings_raw}
    listed = findings_list_from_response(body)
    return {"run_id": str(run_id), "rows": findings_table_rows(listed)}


@router.get(
    "/runs/{run_id}/critic-matrix-table",
    responses={404: PROBLEM_RESPONSE_404},
)
def critic_matrix_table(run_id: UUID, store: StoreDep, _admin: AdminDep) -> dict[str, Any]:
    rows = store.list_run_events(str(run_id))
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=problem("run_not_found", "run not found", details={"run_id": str(run_id)}),
        )
    events: list[dict[str, Any]] = []
    for r in rows:
        d = serialized_event_from_row(r)
        ev = validate_event_dict(d)
        events.append(serialize_event_persistent(ev))
    return {"run_id": str(run_id), "rows": critic_matrix_rows_from_events(events)}
