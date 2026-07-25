from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from broker_client.client import BrokerClient
from compute.broker_route import map_broker_compute_http_error


def test_stage_bind_http_error_no_mcp_fallthrough(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak436-a: under peel, HTTP error dict is returned (no silent MCP retry)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    monkeypatch.setenv("NIMBUSWARE_BROKER_HTTP", "http://broker.test")
    from broker_client.stage_bind import compute as stage

    http = MagicMock()
    http.compute_work.return_value = {"error": "bad", "work": None}
    mcp = MagicMock()
    out = stage.compute_work_via_broker(
        {"action": "list", "kind": "echo"},
        client=mcp,
        http=http,
    )
    assert out.get("error") == "bad"
    mcp.call_tool.assert_not_called()


def test_stage_bind_http_transport_reraises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak436-a: HTTP transport failure re-raises (no MCP fallthrough)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    monkeypatch.setenv("NIMBUSWARE_BROKER_HTTP", "http://broker.test")
    from broker_client.stage_bind import compute as stage

    http = MagicMock()
    http.compute_work.side_effect = RuntimeError("transport down")
    mcp = MagicMock()
    with pytest.raises(RuntimeError, match="transport down"):
        stage.compute_work_via_broker(
            {"action": "list", "kind": "echo"},
            client=mcp,
            http=http,
        )
    mcp.call_tool.assert_not_called()


def test_map_broker_compute_http_error_miss_under_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak436-b/c: COMPUTE=1 maps to broker_miss dict."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    out = map_broker_compute_http_error(
        RuntimeError("down"),
        feature="fleet_mesh",
        miss_extra={"status": "degraded", "queue_depth": 0},
    )
    assert out["via"] == "broker_miss"
    assert out["status"] == "degraded"
    assert out["feature"] == "fleet_mesh"


def test_map_broker_compute_http_error_503_under_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak436-b/c: COMPUTE=2 raises HTTP 503."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "2")
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        map_broker_compute_http_error(RuntimeError("down"), feature="fleet_mesh")
    assert ei.value.status_code == 503


def test_broker_client_session_compute_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak436-e: BrokerClient.session_compute_status wraps shared helper."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    with patch(
        "compute.broker_session_status.broker_session_compute_status",
        return_value={"via": "broker", "nodes": [], "queue_depth": 0},
    ) as mock_status:
        out = BrokerClient(base_url="http://broker.test").session_compute_status(
            "s1", feature="fleet_mesh"
        )
    assert out["via"] == "broker"
    mock_status.assert_called_once_with("s1", feature="fleet_mesh")


def test_context_budget_propagates_capacity_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak436-g: CAPACITY peel miss does not soft-default to weak window."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from projections.builders import context_budget as cb

    with patch(
        "hw.cache.get_cached_profile",
        side_effect=RuntimeError("CAPACITY=1|2 miss"),
    ):
        with pytest.raises(RuntimeError, match="CAPACITY"):
            cb.window_tokens_from_events([])


def test_readiness_memory_propagates_capacity_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak436-g: readiness memory check re-raises under CAPACITY peel."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from maker.readiness import platform as readiness

    with patch(
        "hw.cache.get_cached_profile",
        side_effect=RuntimeError("CAPACITY=1|2 miss"),
    ):
        with pytest.raises(RuntimeError, match="CAPACITY"):
            readiness._check_memory()
