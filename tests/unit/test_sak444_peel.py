from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from compute.broker_route import map_broker_compute_http_error, miss
from maker.services.models import assert_capacity_ok, is_capacity_miss


def test_try_broker_call_removed_from_compute_broker_route() -> None:
    """sak444-c: compute.broker_route.try_broker_call deleted."""
    import compute.broker_route as br

    assert not hasattr(br, "try_broker_call")
    assert callable(map_broker_compute_http_error)
    assert miss("x")["via"] == "broker_miss"


def test_routing_presets_thin_restore(tmp_path: Path) -> None:
    """sak444-b: list/apply routing presets after peel stub restore."""
    import yaml

    from orchestrator.model_routing.presets import (
        apply_routing_preset,
        list_routing_preset_summaries,
    )

    (tmp_path / "configs").mkdir(parents=True)
    (tmp_path / "configs" / "model-routing.yaml").write_text(
        yaml.dump(
            {
                "version": 1,
                "models": {},
                "routing_presets": {
                    "version": 1,
                    "presets": {
                        "local_only": {
                            "label": "Local",
                            "description": "d",
                            "cloud_runtime": {},
                        }
                    },
                },
            },
        ),
        encoding="utf-8",
    )
    rows = list_routing_preset_summaries(tmp_path)
    assert any(r["id"] == "local_only" for r in rows)
    applied = apply_routing_preset(tmp_path, "local_only")
    assert applied["status"] == "applied"
    assert applied["preset_id"] == "local_only"


def test_apply_routing_preset_capacity_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from api.routes import platform_model_routing as pmr

    orch = MagicMock()
    orch.repo_root = Path(".")
    body = pmr.ApplyRoutingPresetBody(preset_id="x")
    with patch(
        "api.routes.platform_model_routing.apply_routing_preset",
        side_effect=RuntimeError("CAPACITY miss"),
    ):
        out = pmr.post_apply_routing_preset(orch, body)
    assert out.get("via") == "broker_miss"
    assert out.get("feature") == "platform_routing_presets_apply"


def test_delegate_control_response_model() -> None:
    """sak444-d: OpenAPI DelegateControlResponse exists."""
    from api.routes.chat_session import DelegateControlResponse

    m = DelegateControlResponse(via="broker_miss", feature="x", error="down")
    assert m.via == "broker_miss"


def test_fleet_mesh_and_hardware_response_models() -> None:
    """sak444-e: OpenAPI response models on fleet mesh + hardware."""
    from api.routes.enterprise.fleet_mesh import FleetMeshStatusResponse
    from api.routes.platform_model_routing import PlatformCapacityResponse

    assert FleetMeshStatusResponse(nodes=[], queue_depth=0).queue_depth == 0
    assert PlatformCapacityResponse(via="broker_miss", hosts=[]).via == "broker_miss"


def test_maker_capacity_miss_helpers() -> None:
    """sak444-g: Maker Python capacity miss helpers."""
    assert is_capacity_miss({"via": "broker_miss"})
    assert is_capacity_miss({"capacity_source": "broker_miss"})
    assert not is_capacity_miss({"models": []})
    assert assert_capacity_ok({"models": []}, feature="t")["models"] == []
    with pytest.raises(RuntimeError, match="broker_miss"):
        assert_capacity_ok({"via": "broker_miss", "error": "x"}, feature="t")


def test_admin_complete_terminate_assert_exports() -> None:
    """sak444-a: admin client exports peel asserts used by complete/terminate."""
    client_path = (
        Path(__file__).resolve().parents[2]
        / "packages"
        / "admin_ui"
        / "src"
        / "api"
        / "client.ts"
    )
    text = client_path.read_text(encoding="utf-8")
    assert "completeWorkUnit" in text
    assert "terminateRestartWorkUnit" in text
    assert "assertBrokerComputeRecordOk" in text


def test_map_broker_compute_http_error_under_compute_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    out = map_broker_compute_http_error(
        RuntimeError("down"),
        feature="fleet_mesh",
        miss_extra={"nodes": [], "queue_depth": 0},
    )
    assert out["via"] == "broker_miss"
    assert out["nodes"] == []
