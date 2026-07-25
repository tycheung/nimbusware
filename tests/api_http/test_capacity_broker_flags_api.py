from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api.routes.platform_hardware import _hardware_response


def _assert_capacity_2_problem(exc: HTTPException) -> None:
    assert exc.status_code == 503
    detail = exc.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_capacity_only"


def test_platform_hardware_capacity_1_broker_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    orch = MagicMock()
    orch.repo_root = "."
    profile = MagicMock()
    profile.model_dump_public.return_value = {"tier": "strong"}
    profile.platform = "broker"
    with (
        patch(
            "orchestrator._pipeline.resource_governor_resolve.resolve_resource_governor",
            return_value=(
                profile,
                {"hardware_tier": "strong", "capacity_source": "broker"},
            ),
        ),
        patch(
            "api.routes.platform_hardware.governor_from_metadata",
            return_value=MagicMock(to_metadata=lambda: {"hardware_tier": "strong"}),
        ),
        patch(
            "api.routes.platform_hardware.rank_models",
            return_value=[{"tag": "m1"}],
        ),
    ):
        body = _hardware_response(orch, remote_host=None)
    body.pop("_governor", None)
    assert body.get("capacity_source") == "broker"
    assert body.get("fit_via") == "local"
    assert len(body.get("models_ranked") or []) == 1


def test_platform_hardware_capacity_1_resolve_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    orch = MagicMock()
    orch.repo_root = "."
    with patch(
        "orchestrator._pipeline.resource_governor_resolve.resolve_resource_governor",
        side_effect=RuntimeError("CAPACITY=1|2 miss"),
    ):
        with pytest.raises(RuntimeError, match="CAPACITY"):
            _hardware_response(orch, remote_host=None)


def test_platform_hardware_get_returns_structured_miss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak441-c: GET handler returns broker_miss body under CAPACITY=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from api.routes import platform_hardware as ph

    orch = MagicMock()
    with patch.object(
        ph,
        "_hardware_response",
        side_effect=RuntimeError("CAPACITY=1|2 miss"),
    ):
        body = ph.get_platform_hardware(orch, remote_host=None, binding_id=None)
    assert body.get("capacity_source") == "broker_miss"
    assert body.get("status") == "degraded"
    assert body.get("via") == "broker_miss"


def test_platform_hardware_under_capacity_2_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak491-b: platform hardware GET maps broker failure to 503 under CAPACITY=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")
    from api.routes import platform_hardware as ph

    orch = MagicMock()
    with patch.object(
        ph,
        "_hardware_response",
        side_effect=RuntimeError("CAPACITY=1|2 miss"),
    ):
        with pytest.raises(HTTPException) as ei:
            ph.get_platform_hardware(orch, remote_host=None, binding_id=None)
    _assert_capacity_2_problem(ei.value)


def test_platform_hardware_remote_host_under_capacity_2_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak491-b: remote_host probe refuse maps to 503 under CAPACITY=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")
    from api.routes import platform_hardware as ph

    orch = MagicMock()
    with pytest.raises(HTTPException) as ei:
        ph.get_platform_hardware(orch, remote_host="worker.test", binding_id=None)
    _assert_capacity_2_problem(ei.value)


def test_models_ranked_under_capacity_2_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak491-b: models/ranked maps broker failure to 503 under CAPACITY=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")
    from api.routes import platform_model_routing as pmr

    orch = MagicMock()
    orch.repo_root = "."
    with patch(
        "api.routes.platform_model_routing.get_cached_profile",
        side_effect=RuntimeError("CAPACITY miss"),
    ):
        with pytest.raises(HTTPException) as ei:
            pmr.get_models_ranked(orch)
    _assert_capacity_2_problem(ei.value)


def test_models_dependencies_under_capacity_2_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak491-b: models/dependencies maps broker failure to 503 under CAPACITY=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")
    from api.routes import platform_model_routing as pmr

    orch = MagicMock()
    store = MagicMock()
    with patch(
        "api.routes.platform_model_routing.build_platform_readiness",
        side_effect=RuntimeError("memory import unavailable"),
    ):
        with pytest.raises(HTTPException) as ei:
            pmr.get_model_dependencies(orch, store)
    _assert_capacity_2_problem(ei.value)


def test_platform_readiness_under_capacity_2_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sak491-b / sak493-a: platform/readiness maps broker failure to 503 under CAPACITY=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")
    from api.routes import platform as plat

    orch = MagicMock()
    store = MagicMock()
    with patch(
        "api.routes.platform.build_platform_readiness",
        side_effect=RuntimeError("readiness down"),
    ):
        with pytest.raises(HTTPException) as ei:
            plat.get_platform_readiness(orch, store)
    _assert_capacity_2_problem(ei.value)
