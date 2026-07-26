from __future__ import annotations

import json
from typing import Any

import httpx

from broker_client.http import auth_headers

SESSION_HEADER = "mcp-session-id"
MCP_PROTOCOL_VERSION = "2024-11-05"
CLIENT_NAME = "nimbusware-broker-client"
CLIENT_VERSION = "0.1.0"
# Streamable HTTP requires both (sak MCP http); missing → 406.
MCP_ACCEPT = "application/json, text/event-stream"


def initialize_params() -> dict[str, Any]:
    return {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
    }


def rpc_headers(token: str, session_id: str | None) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": MCP_ACCEPT,
        **auth_headers(token),
    }
    if session_id:
        headers[SESSION_HEADER] = session_id
    return headers


def body_from_response(response: httpx.Response) -> Any:
    raw_text = getattr(response, "text", None)
    text = raw_text if isinstance(raw_text, str) else ""
    headers = getattr(response, "headers", None) or {}
    content_type = str(headers.get("content-type") or "").lower()
    if "text/event-stream" in content_type or text.lstrip().startswith("data:"):
        for line in text.splitlines():
            if line.startswith("data:"):
                raw = line[5:].strip()
                if raw:
                    return json.loads(raw)
        raise ValueError("empty SSE MCP response")
    return response.json()


def build_payload(
    rpc_id: int,
    method: str,
    params: dict[str, Any] | None,
    *,
    notification: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": method,
    }
    if not notification:
        payload["id"] = rpc_id
    if params is not None:
        payload["params"] = params
    return payload


def session_from_body(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    for key in ("sessionId", "session_id", "mcp-session-id"):
        val = body.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    result = body.get("result")
    if isinstance(result, dict):
        for key in ("sessionId", "session_id", "mcp-session-id"):
            val = result.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None


def session_from_response(response: httpx.Response) -> str | None:
    header_val = response.headers.get(SESSION_HEADER)
    if header_val and header_val.strip():
        return header_val.strip()
    try:
        return session_from_body(body_from_response(response))
    except (ValueError, json.JSONDecodeError):
        return None


def post_json_rpc(
    base_url: str,
    *,
    method: str,
    params: dict[str, Any] | None,
    rpc_id: int,
    token: str,
    session_id: str | None,
    timeout: float,
    client: httpx.Client | None,
    notification: bool = False,
) -> httpx.Response:
    payload = build_payload(rpc_id, method, params, notification=notification)
    headers = rpc_headers(token, session_id)
    if client is not None:
        response = client.post(base_url, json=payload, headers=headers, timeout=timeout)
        # notifications/initialized → 202 with empty body
        if notification and response.status_code in (200, 202):
            return response
        response.raise_for_status()
        return response
    with httpx.Client(timeout=timeout) as owned:
        response = owned.post(base_url, json=payload, headers=headers)
        if notification and response.status_code in (200, 202):
            return response
        response.raise_for_status()
        return response


def parse_rpc_result(body: Any, *, operation: str) -> Any:
    if isinstance(body, dict) and "error" in body:
        err = body["error"]
        message = err.get("message", err) if isinstance(err, dict) else err
        raise RuntimeError(f"MCP {operation} failed: {message}")
    if isinstance(body, dict):
        return body.get("result", body)
    return body
