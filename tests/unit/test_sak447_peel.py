from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_maker_settings_miss_helpers() -> None:
    """sak447-a."""
    root = Path(__file__).resolve().parents[2] / "packages" / "maker_web" / "static" / "js"
    opt = (root / "tabs" / "settings_optimizer_ui.js").read_text(encoding="utf-8")
    agents = (root / "tabs" / "chat_agents_ui.js").read_text(encoding="utf-8")
    routing = (root / "tabs" / "settings_agent_routing_ui.js").read_text(encoding="utf-8")
    assert "toastIfMiss" in opt and "Optimizer weights" in opt
    assert "maker-chat-agents-miss" in agents
    assert "Agent model bindings unavailable" in routing


def test_drawer_no_empty_catch_masquerade() -> None:
    """sak447-b: drawer catch maps to broker_miss, not empty catalogs."""
    path = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "maker_web"
        / "static"
        / "js"
        / "tabs"
        / "chat_model_drawer_ui.js"
    )
    text = path.read_text(encoding="utf-8")
    assert ".catch(() => ({ roles: []" not in text
    assert 'via: "broker_miss"' in text


def test_readiness_capacity_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak447-c."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from api.routes import platform as plat

    orch = MagicMock()
    orch.repo_root = Path(".")
    store = MagicMock()
    with patch(
        "api.routes.platform.build_platform_readiness",
        side_effect=RuntimeError("CAPACITY miss"),
    ):
        out = plat.get_platform_readiness(orch, store)
    assert out.get("via") == "broker_miss"
    assert out.get("feature") == "platform_readiness"


def test_platform_readiness_onboarding_openapi() -> None:
    """sak447-d."""
    from api.routes.platform import PlatformOnboardingResponse, PlatformReadinessResponse

    assert PlatformReadinessResponse(status="ok").status == "ok"
    assert PlatformOnboardingResponse(onboarded=True).onboarded is True


def test_provider_connections_openapi() -> None:
    """sak447-e."""
    from api.routes.provider_connections import (
        ProviderConnectionsListResponse,
        ProviderPresetsResponse,
    )

    assert ProviderPresetsResponse(providers=[]).providers == []
    assert ProviderConnectionsListResponse(connections=[]).connections == []


def test_role_claim_openapi() -> None:
    """sak447-f."""
    from api.routes.chat_collab import RoleClaimResponse

    assert RoleClaimResponse(ok=True, event="workload.role_claimed").ok is True


def test_broker_client_raw_compute_post_assert() -> None:
    """sak447-g."""
    from broker_client.client import BrokerClient

    client = BrokerClient(base_url="http://example.test", client=MagicMock())
    with patch(
        "broker_client.client.post_json",
        return_value={"error": "down"},
    ):
        with pytest.raises(RuntimeError, match="broker_miss"):
            client.compute_work({"action": "enqueue", "kind": "x"})
    with patch(
        "broker_client.client.post_json",
        return_value={"error": "queue empty", "work": None},
    ):
        raw = client.compute_work({"action": "claim", "node_id": "n1"})
    assert raw["error"] == "queue empty"


def test_admin_peel_assert_module() -> None:
    """sak447-h: peel asserts live in peel_assert.ts and re-export from client."""
    api = Path(__file__).resolve().parents[2] / "packages" / "admin_ui" / "src" / "api"
    peel = (api / "peel_assert.ts").read_text(encoding="utf-8")
    client = (api / "client.ts").read_text(encoding="utf-8")
    assert "assertBrokerComputeRecordOk" in peel
    assert 'from "./peel_assert"' in client


def test_delegate_control_no_dead_exhaust_block() -> None:
    """sak447-i: redundant broker_compute_enabled exhaust path removed."""
    path = Path(__file__).resolve().parents[2] / "packages" / "api" / "routes" / "chat_session.py"
    text = path.read_text(encoding="utf-8")
    assert "delegate-control broker path exhausted" not in text
    assert "sak447-i" in text
