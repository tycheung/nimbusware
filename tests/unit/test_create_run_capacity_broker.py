from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import orchestrator._pipeline.resource_governor_resolve as rgr


def test_resolve_resource_governor_uses_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    broker_gov = {
        "snapshot": {
            "total_ram_mb": 32_768,
            "available_ram_mb": 16_384,
            "cpu_logical": 8,
            "source": "fake",
        },
        "via": "broker",
    }
    monkeypatch.setattr(rgr, "try_broker_capacity_probe", lambda: broker_gov)

    def _boom(_profile: object = None) -> object:
        raise AssertionError(
            "get_cached_profile / governor_for_profile should not run on broker hit"
        )

    monkeypatch.setattr(rgr, "get_cached_profile", _boom)
    monkeypatch.setattr(rgr, "governor_for_profile", _boom)
    hw, gov = rgr.resolve_resource_governor()
    assert gov["hardware_tier"] == "strong"
    assert gov["max_parallel_writer_stages"] == 3
    assert gov["capacity_source"] == "broker"
    assert hw.tier == "strong"
    assert hw.ram_total_gb == 32.0


def test_resolve_resource_governor_flag_off_uses_hw(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_CAPACITY", raising=False)
    monkeypatch.setattr(rgr, "try_broker_capacity_probe", lambda: None)
    monkeypatch.setattr(rgr, "get_cached_profile", lambda: object())
    monkeypatch.setattr(
        rgr,
        "governor_for_profile",
        lambda _p: MagicMock(to_metadata=lambda: {"hardware_tier": "weak", "via": "hw"}),
    )
    _hw, gov = rgr.resolve_resource_governor()
    assert gov["via"] == "hw"


def test_resolve_resource_governor_broker_only_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")

    def _boom() -> dict:
        raise RuntimeError("capacity down")

    monkeypatch.setattr(rgr, "try_broker_capacity_probe", _boom)
    with pytest.raises(RuntimeError, match="capacity down"):
        rgr.resolve_resource_governor()
