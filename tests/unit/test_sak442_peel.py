from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from hw.capacity_route import map_broker_capacity_http_miss


def test_capacity_1_miss_body(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    body = map_broker_capacity_http_miss(RuntimeError("down"), feature="fleet")
    assert body["capacity_source"] == "broker_miss"
    assert body["hosts"] == []


def test_capacity_2_miss_raises_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")
    with pytest.raises(HTTPException) as ei:
        map_broker_capacity_http_miss(RuntimeError("down"), feature="platform_hardware")
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_capacity_only"


def test_fleet_rescan_returns_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from api.routes import platform_hardware as ph

    with (
        patch("api.routes.platform_hardware.is_enterprise", return_value=True),
        patch(
            "hw.fleet_hardware.rescan_fleet_hardware_hosts",
            side_effect=RuntimeError("CAPACITY miss"),
        ),
    ):
        body = ph.post_platform_hardware_fleet_rescan()
    assert body.get("via") == "broker_miss"
    assert body.get("hosts") == []
    assert body.get("feature") == "platform_hardware_fleet_rescan"


def test_models_ranked_returns_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from api.routes import platform_model_routing as pmr

    orch = MagicMock()
    orch.repo_root = "."
    with patch(
        "api.routes.platform_model_routing.get_cached_profile",
        side_effect=RuntimeError("CAPACITY=1|2 miss"),
    ):
        body = pmr.get_models_ranked(orch)
    assert body.get("capacity_source") == "broker_miss"
    assert body.get("models") == []
    assert body.get("feature") == "platform_models_ranked"


def test_broker_client_list_nodes_asserts(monkeypatch: pytest.MonkeyPatch) -> None:
    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test")
    with patch.object(
        client,
        "compute_nodes",
        return_value={"error": "down", "nodes": []},
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.list_nodes_filtered(session_id="s1")


def test_broker_client_list_work_asserts() -> None:
    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test")
    with patch.object(
        client,
        "compute_work",
        return_value={"work": None},
    ):
        with pytest.raises(RuntimeError, match="non-list"):
            client.list_work_filtered()
