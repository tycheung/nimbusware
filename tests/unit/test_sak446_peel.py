from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_participant_bindings_openapi() -> None:
    """sak446-a."""
    from api.routes.chat_session import ParticipantBindingsResponse

    assert ParticipantBindingsResponse(user_id="u", roles={}).user_id == "u"


def test_model_bindings_openapi() -> None:
    """sak446-b."""
    from api.routes.model_bindings import (
        ModelBindingsDefaultsResponse,
        ModelBindingsPreflightResponse,
        ModelBindingsRolesResponse,
    )

    assert ModelBindingsRolesResponse(roles=[]).roles == []
    assert ModelBindingsDefaultsResponse(defaults={}).defaults == {}
    assert ModelBindingsPreflightResponse(ok=True).ok is True


def test_platform_optimizer_weights_openapi() -> None:
    """sak446-c."""
    from api.routes.platform import PlatformOptimizerWeightsResponse

    assert PlatformOptimizerWeightsResponse(weights={"a": 1.0}).weights["a"] == 1.0


def test_remote_host_capacity_refuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak446-d: remote_host SSH probe refuses under CAPACITY=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from api.routes import platform_hardware as ph

    orch = MagicMock()
    orch.repo_root = Path(".")
    with pytest.raises(RuntimeError, match="remote_host|CAPACITY|capacity"):
        ph._hardware_response(orch, remote_host="ssh://host")


def test_rust_assert_capacity_ok_export() -> None:
    """sak446-e: Rust SDK exports assert_capacity_ok (source check)."""
    client_rs = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "crates"
        / "sdk"
        / "src"
        / "client.rs"
    )
    text = client_rs.read_text(encoding="utf-8")
    assert "fn assert_capacity_ok" in text
    assert "assert_list_ok(&raw, \"modules\")" in text


def test_python_sdk_capacity_modules_assert() -> None:
    """sak446-f."""
    import sys

    sdk_src = (
        Path(__file__).resolve().parents[3]
        / "SwissArmyNoife"
        / "sdks"
        / "python"
        / "src"
    )
    sys.path.insert(0, str(sdk_src))
    from swissarmynoife.client import SakClient

    assert SakClient.assert_capacity_ok({"snapshot": {}})["snapshot"] == {}
    with pytest.raises(RuntimeError, match="broker_miss"):
        SakClient.assert_capacity_ok({"error": "down"})
    assert SakClient.assert_list_ok(
        {"modules": []}, list_key="modules", feature="t"
    )["modules"] == []


def test_broker_client_list_modules_assert() -> None:
    """sak446-g."""
    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch(
        "broker_client.client.get_json",
        return_value={"error": "x", "modules": []},
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.list_modules()
    with patch("broker_client.client.get_json", return_value={"error": "gone"}):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.get_module("m1")


def test_maker_web_routing_catalog_miss_helpers() -> None:
    """sak446-h."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js"
    routing = (root / "tabs" / "settings_agent_routing_ui.js").read_text(encoding="utf-8")
    models = (root / "tabs" / "models_local_ui.js").read_text(encoding="utf-8")
    drawer = (root / "tabs" / "chat_model_drawer_ui.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in routing and "Routing presets unavailable" in routing
    assert "isBrokerMiss(info)" in models or "isBrokerMiss(info)" in models.replace(" ", "")
    assert "maker-chat-model-drawer-miss" in drawer


def test_admin_ui_catalog_fleet_miss() -> None:
    """sak446-i."""
    admin = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src" / "pages"
    hw = (admin / "HardwarePage.tsx").read_text(encoding="utf-8")
    fleet = (admin / "FleetPage.tsx").read_text(encoding="utf-8")
    assert "admin-hw-catalog-miss" in hw
    assert "setCapacityPeelMiss" in fleet and "fleet hardware peel miss" in fleet
