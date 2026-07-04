from __future__ import annotations

import json
import sys
from typing import Any

from mcp.tool_specs import MCP_TIER1_TOOLS, TOOL_SPECS, tool_spec_by_name
from mcp.tools import call_tool

_PROTOCOL_VERSION = "2024-11-05"
_SERVER_INFO = {"name": "nimbusware-mcp", "version": "0.1.0"}


def _read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        decoded = line.decode("utf-8").strip()
        if not decoded:
            break
        key, _, value = decoded.partition(":")
        headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = sys.stdin.buffer.read(length)
    parsed: object = json.loads(body.decode("utf-8"))
    if not isinstance(parsed, dict):
        return None
    return parsed


def _write_message(payload: dict[str, Any]) -> None:
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    header = f"Content-Length: {len(data)}\r\n\r\n".encode("ascii")
    sys.stdout.buffer.write(header)
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def _handle_request(msg: dict[str, Any]) -> dict[str, Any] | None:
    method = msg.get("method")
    req_id = msg.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": _SERVER_INFO,
            },
        }
    if method == "tools/list":
        raw_list_params = msg.get("params")
        list_params: dict[str, Any] = raw_list_params if isinstance(raw_list_params, dict) else {}
        tier = str(list_params.get("tier") or "eager").strip().lower()
        if tier == "lazy":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {"name": n, "description": "lazy schema; call tool_schema for details"}
                        for n in sorted(MCP_TIER1_TOOLS)
                    ],
                },
            }
        if tier == "schema":
            name = str(list_params.get("name") or "").strip()
            spec = tool_spec_by_name(name)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tool": spec or {}},
            }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOL_SPECS},
        }
    if method == "tools/call":
        raw_params = msg.get("params")
        params: dict[str, Any] = raw_params if isinstance(raw_params, dict) else {}
        name = str(params.get("name") or "")
        raw_args = params.get("arguments")
        arguments: dict[str, Any] = raw_args if isinstance(raw_args, dict) else {}
        try:
            result = call_tool(name, arguments)
        except Exception as exc:  # noqa: BLE001
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                },
            }
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    if req_id is None:
        return None
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def run_stdio_server() -> None:
    while True:
        msg = _read_message()
        if msg is None:
            break
        response = _handle_request(msg)
        if response is not None:
            _write_message(response)
