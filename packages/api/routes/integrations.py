from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from api.admin import AdminDep, require_admin_token
from api.errors import problem
from api.schemas.openapi import PROBLEM_RESPONSE_401
from console.operator_chat_core import ChatState, process_user_message

router = APIRouter(prefix="/integrations", tags=["admin"])

_webhook_sessions: dict[str, ChatState] = {}


class ExternalChatWebhookBody(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    source: str = Field(default="generic", max_length=64)
    session_id: str = Field(default="external", max_length=128)


class ExternalChatWebhookResponse(BaseModel):
    reply: str
    last_run_id: str = ""
    source: str = "generic"
    note: str = (
        "External webhook for run steering from Slack/Teams/etc. "
        "In-product operator chat: Maker Chat (#/chat) and Admin operator chat."
    )


def _webhook_secret() -> str:
    from env.settings_resolve import resolve_str

    return resolve_str("NIMBUSWARE_WEBHOOK_SECRET", default="").strip()


@router.get("/external-chat")
def external_chat_capabilities(_admin: AdminDep) -> dict[str, str]:
    return {
        "scope": "external_run_steering",
        "docs": "docs/integrations-external-chat.md",
        "in_product_chat": "Maker #/chat, Admin operator chat, MCP nimbusware-mcp",
        "supported_commands": "/run, /timeline, /status, /agent, /help",
        "steering_prefixes": "[patch], [steer], [skip], [build]",
        "mention_routing": "@frontend, @backend, @qa, … on active run (session_id persists last_run_id)",
    }


@router.post(
    "/external-chat/webhook",
    response_model=ExternalChatWebhookResponse,
    responses={401: PROBLEM_RESPONSE_401},
)
def external_chat_webhook(
    body: ExternalChatWebhookBody,
    x_nimbusware_webhook_secret: Annotated[str | None, Header()] = None,
    x_nimbusware_admin_token: Annotated[str | None, Header()] = None,
) -> ExternalChatWebhookResponse:
    secret = _webhook_secret()
    if secret:
        provided = (x_nimbusware_webhook_secret or "").strip()
        if not provided or not secrets.compare_digest(provided, secret):
            raise HTTPException(
                status_code=401,
                detail=problem("webhook_unauthorized", "invalid webhook secret"),
            )
    else:
        require_admin_token(x_nimbusware_admin_token)

    key = body.session_id.strip()[:128] or "external"
    state = _webhook_sessions.setdefault(key, ChatState())
    reply = process_user_message(body.text, state)
    return ExternalChatWebhookResponse(
        reply=reply,
        last_run_id=state.last_run_id,
        source=body.source,
    )
