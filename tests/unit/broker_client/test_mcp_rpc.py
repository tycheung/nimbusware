from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from broker_client.mcp_rpc import (
    SESSION_HEADER,
    initialize_params,
    parse_rpc_result,
    rpc_headers,
    session_from_body,
    session_from_response,
)


def test_initialize_params_contract() -> None:
    params = initialize_params()
    assert params["protocolVersion"] == "2024-11-05"
    assert params["clientInfo"]["name"] == "nimbusware-broker-client"


def test_rpc_headers_includes_session_when_set() -> None:
    headers = rpc_headers("tok", "sess-1")
    assert headers["Authorization"] == "Bearer tok"
    assert headers[SESSION_HEADER] == "sess-1"
    assert headers["Accept"] == "application/json, text/event-stream"


def test_body_from_response_parses_sse() -> None:
    from broker_client.mcp_rpc import body_from_response

    response = MagicMock(spec=httpx.Response)
    response.headers = {"content-type": "text/event-stream"}
    response.text = 'data: {"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n\n'
    assert body_from_response(response) == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"ok": True},
    }


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"sessionId": " top "}, "top"),
        ({"result": {"session_id": "nested"}}, "nested"),
        ({"error": "nope"}, None),
    ],
)
def test_session_from_body(body: dict, expected: str | None) -> None:
    assert session_from_body(body) == expected


def test_session_from_response_prefers_header() -> None:
    response = MagicMock(spec=httpx.Response)
    response.headers = {SESSION_HEADER: "header-sess"}
    response.json.return_value = {"sessionId": "body-sess"}
    assert session_from_response(response) == "header-sess"


def test_parse_rpc_result_raises_on_error() -> None:
    with pytest.raises(RuntimeError, match="tools/list failed"):
        parse_rpc_result({"error": {"message": "denied"}}, operation="tools/list")


def test_parse_rpc_result_returns_result() -> None:
    assert parse_rpc_result({"result": {"tools": []}}, operation="tools/list") == {"tools": []}
