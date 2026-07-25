from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from broker_client import BrokerMcpClient
from broker_client.mcp_client import resolve_mcp_url


def test_resolve_mcp_url_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_MCP", raising=False)
    assert resolve_mcp_url() == "http://127.0.0.1:8080/mcp"


def test_resolve_mcp_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_MCP", "http://broker.test:8090/mcp/")
    assert resolve_mcp_url() == "http://broker.test:8090/mcp"


def test_initialize_posts_json_rpc_and_stores_session_header() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    init_response = MagicMock()
    init_response.json.return_value = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"protocolVersion": "2024-11-05"},
    }
    init_response.raise_for_status = MagicMock()
    init_response.headers = {"mcp-session-id": "sess-abc"}
    notif_response = MagicMock()
    notif_response.status_code = 202
    notif_response.raise_for_status = MagicMock()
    notif_response.headers = {}
    notif_response.text = ""
    mock_client.post.side_effect = [init_response, notif_response]

    client = BrokerMcpClient("http://127.0.0.1:8080/mcp", client=mock_client)
    out = client.initialize()

    assert mock_client.post.call_count == 2
    init_call, notif_call = mock_client.post.call_args_list
    assert init_call.kwargs["json"]["method"] == "initialize"
    assert init_call.kwargs["json"]["params"]["protocolVersion"] == "2024-11-05"
    assert init_call.kwargs["json"]["params"]["clientInfo"]["name"] == "nimbusware-broker-client"
    assert notif_call.kwargs["json"]["method"] == "notifications/initialized"
    assert "id" not in notif_call.kwargs["json"]
    assert client.session_id == "sess-abc"
    assert out == {"protocolVersion": "2024-11-05"}


def test_list_tools_initialize_then_tools_list(mock_post_sequence) -> None:
    mock_client = MagicMock(spec=httpx.Client)
    posts = mock_post_sequence(
        mock_client,
        [
            {"jsonrpc": "2.0", "id": 1, "result": {"sessionId": "body-sess"}},
            {},  # notifications/initialized
            {"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "ping"}]}},
        ],
    )
    posts[1].status_code = 202
    posts[1].text = ""

    client = BrokerMcpClient("http://127.0.0.1:8080/mcp", client=mock_client)
    out = client.list_tools()

    assert mock_client.post.call_count == 3
    list_call = mock_client.post.call_args_list[2]
    assert list_call.kwargs["json"]["method"] == "tools/list"
    assert list_call.kwargs["headers"]["mcp-session-id"] == "body-sess"
    assert out == {"tools": [{"name": "ping"}]}


def test_tools_list_alias_delegates_to_list_tools(mock_post_sequence) -> None:
    mock_client = MagicMock(spec=httpx.Client)
    posts = mock_post_sequence(
        mock_client,
        [
            {"jsonrpc": "2.0", "id": 1, "result": {}},
            {},
            {"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": "catalog_list"}]}},
        ],
    )
    posts[1].status_code = 202
    posts[1].text = ""

    client = BrokerMcpClient("http://127.0.0.1:8080/mcp", client=mock_client)
    out = client.tools_list()

    list_call = mock_client.post.call_args_list[2]
    assert list_call.kwargs["json"]["method"] == "tools/list"
    assert out == {"tools": [{"name": "catalog_list"}]}
