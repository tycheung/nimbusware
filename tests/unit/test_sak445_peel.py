from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from maker.services.models import assert_capacity_ok, is_capacity_miss


def test_capacity_try_broker_call_gone() -> None:
    """sak445-a: dead try_broker_call / try_capacity_or_refuse removed."""
    from hw import capacity_route as cr

    assert not hasattr(cr, "try_broker_call")
    assert not hasattr(cr, "try_capacity_or_refuse")
    assert callable(cr.map_broker_capacity_http_miss)


def test_routing_presets_apply_openapi_model() -> None:
    """sak445-b: PlatformCapacityResponse covers apply miss/success fields."""
    from api.routes.platform_model_routing import PlatformCapacityResponse

    m = PlatformCapacityResponse(
        via="broker_miss",
        feature="platform_routing_presets_apply",
        preset_id="x",
        status="degraded",
    )
    assert m.via == "broker_miss"
    assert m.preset_id == "x"


def test_platform_catalog_presets_deps_openapi() -> None:
    """sak445-c: OpenAPI response models for catalog/presets/deps."""
    from api.routes.platform_model_routing import (
        CatalogInfoResponse,
        ModelDependenciesResponse,
        RoutingPresetsListResponse,
    )

    assert CatalogInfoResponse(model_count=1).model_count == 1
    assert RoutingPresetsListResponse(presets=[]).presets == []
    assert ModelDependenciesResponse(ollama_reachable=False).ollama_reachable is False


def test_optimizer_weights_openapi() -> None:
    """sak445-d: SessionOptimizerWeightsResponse exists."""
    from api.routes.chat_session import SessionOptimizerWeightsResponse

    m = SessionOptimizerWeightsResponse(priority=["a"], weights={"a": 1.0})
    assert m.priority == ["a"]


def test_maker_web_compute_miss_helpers_present() -> None:
    """sak445-e: Maker web surfaces import broker_miss helpers."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js"
    chat = (root / "tabs" / "chat_session_ui.js").read_text(encoding="utf-8")
    accessible = (root / "tabs" / "accessible_compute_ui.js").read_text(encoding="utf-8")
    run_card = (root / "tabs" / "chat_run_card_ui.js").read_text(encoding="utf-8")
    assert "isDomainPeelMiss" in chat and "maker-chat-compute-miss" in chat
    assert "maker-accessible-compute-miss" in accessible
    assert "computeMiss" in run_card


def test_broker_client_list_capacity_assert() -> None:
    """sak445-f: BrokerClient list/capacity raise on error dicts."""
    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch("broker_client.client.get_json", return_value={"error": "down", "work": []}):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.list_work()
    with patch("broker_client.client.get_json", return_value={"error": "down", "nodes": []}):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.list_nodes()
    with patch("broker_client.client.get_json", return_value={"error": "cap down"}):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.capacity()
    with patch(
        "broker_client.client.get_json",
        return_value={"snapshot": {"total_ram_mb": 1}},
    ):
        assert client.capacity()["snapshot"]["total_ram_mb"] == 1


def test_python_sdk_assert_record_ok() -> None:
    """sak445-g: Python SakClient assert_record_ok."""
    import sys

    sdk_src = Path(__file__).resolve().parents[3] / "SwissArmyNoife" / "sdks" / "python" / "src"
    sys.path.insert(0, str(sdk_src))
    from swissarmynoife.client import SakClient

    assert (
        SakClient.assert_record_ok({"work": {"id": "w1"}}, record_key="work")["work"]["id"] == "w1"
    )
    with pytest.raises(RuntimeError, match="broker_miss"):
        SakClient.assert_record_ok({"error": "down"}, record_key="work")


def test_capacity_source_no_fake_masquerade() -> None:
    """sak445-h: platform=fake does not upgrade capacity_source to broker."""
    from api.routes import platform_hardware as ph

    orch = MagicMock()
    orch.repo_root = Path(".")
    profile = MagicMock()
    profile.platform = "fake"
    profile.model_dump_public.return_value = {"platform": "fake", "tier": "t"}
    with (
        patch(
            "orchestrator._pipeline.resource_governor_resolve.resolve_resource_governor",
            return_value=(profile, {"capacity_source": "local"}),
        ),
        patch("api.routes.platform_hardware.rank_models", return_value=[]),
        patch(
            "api.routes.platform_hardware.governor_from_metadata",
            return_value=None,
        ),
        patch(
            "api.routes.platform_hardware.governor_for_profile",
            return_value=MagicMock(to_metadata=lambda: {}),
        ),
    ):
        body = ph._hardware_response(orch, remote_host=None)
    assert body["capacity_source"] == "local"


def test_maker_deps_assert_capacity_ok() -> None:
    """sak445-h: fetch_model_dependencies uses capacity assert."""
    assert is_capacity_miss({"via": "broker_miss"})
    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_capacity_ok({"via": "broker_miss"}, feature="deps")
    assert (
        assert_capacity_ok({"ollama_reachable": True}, feature="deps")["ollama_reachable"] is True
    )
