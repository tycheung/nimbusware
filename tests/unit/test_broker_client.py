from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from broker_client import BrokerClient
from broker_client.http import normalize_base_url


def test_normalize_base_url_strips_trailing_slash() -> None:
    assert normalize_base_url("http://127.0.0.1:8787/") == "http://127.0.0.1:8787"
    assert normalize_base_url("  http://127.0.0.1:8787/  ") == "http://127.0.0.1:8787"


def test_get_json_backward_compat_import_from_http() -> None:
    from broker_client.http import get_json as http_get_json
    from broker_client.http_get import get_json as direct_get_json

    assert http_get_json is direct_get_json


def test_broker_client_default_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_HTTP", raising=False)
    client = BrokerClient()
    assert client.base_url == "http://127.0.0.1:8787"


def test_broker_client_base_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_HTTP", "http://broker.test:9999/")
    client = BrokerClient()
    assert client.base_url == "http://broker.test:9999"


def test_health_calls_http_admin() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    broker = BrokerClient("http://127.0.0.1:8787", client=mock_client)
    out = broker.health()

    mock_client.get.assert_called_once_with(
        "http://127.0.0.1:8787/health",
        headers={},
        timeout=15.0,
    )
    assert out == {"ok": True}


def test_list_modules_calls_http_admin() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock()
    mock_response.json.return_value = {"modules": []}
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    broker = BrokerClient("http://127.0.0.1:8787", client=mock_client)
    out = broker.list_modules()

    mock_client.get.assert_called_once_with(
        "http://127.0.0.1:8787/v1/sak/modules",
        headers={},
        timeout=15.0,
    )
    assert out == {"modules": []}


def test_get_module_calls_http_admin() -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "demo.wasm", "version": "1.0.0"}
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    broker = BrokerClient("http://127.0.0.1:8787", client=mock_client)
    out = broker.get_module("demo.wasm")

    mock_client.get.assert_called_once_with(
        "http://127.0.0.1:8787/v1/sak/modules/demo.wasm",
        headers={},
        timeout=15.0,
    )
    assert out == {"id": "demo.wasm", "version": "1.0.0"}


def test_auth_header_when_token_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_TOKEN", "sk_test")
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    broker = BrokerClient("http://127.0.0.1:8787", client=mock_client)
    broker.health()

    mock_client.get.assert_called_once_with(
        "http://127.0.0.1:8787/health",
        headers={"Authorization": "Bearer sk_test"},
        timeout=15.0,
    )


def test_health_uses_context_client_when_not_injected() -> None:
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "ok"}
    mock_response.raise_for_status = MagicMock()
    mock_owned = MagicMock()
    mock_owned.get.return_value = mock_response

    with patch("broker_client.http_get.httpx.Client") as client_cls:
        client_cls.return_value.__enter__.return_value = mock_owned
        out = BrokerClient("http://127.0.0.1:8787/").health()

    client_cls.assert_called_once_with(timeout=15.0)
    mock_owned.get.assert_called_once_with(
        "http://127.0.0.1:8787/health",
        headers={},
    )
    assert out == {"status": "ok"}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("capacity", "/v1/sak/capacity"),
        ("list_work", "/v1/sak/compute/work"),
        ("list_nodes", "/v1/sak/compute/nodes"),
    ],
)
def test_capacity_compute_helpers(method: str, path: str) -> None:
    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock()
    mock_response.json.return_value = {"items": []}
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response

    broker = BrokerClient("http://127.0.0.1:8787", client=mock_client)
    out = getattr(broker, method)()

    mock_client.get.assert_called_once_with(
        f"http://127.0.0.1:8787{path}",
        headers={},
        timeout=15.0,
    )
    assert out == {"items": []}
