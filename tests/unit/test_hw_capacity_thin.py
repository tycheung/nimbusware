from __future__ import annotations

from unittest.mock import patch

import pytest

from hw.profile import profile_from_probe


def test_probe_hardware_broker_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    monkeypatch.delenv("NIMBUSWARE_HW_FIXTURE", raising=False)
    from hw.probe import probe_hardware

    with patch(
        "broker_client.capacity_bridge.try_broker_capacity_probe",
        return_value={
            "snapshot": {
                "total_ram_mb": 32768,
                "available_ram_mb": 16384,
                "cpu_logical": 8,
                "source": "fake",
            }
        },
    ):
        out = probe_hardware()
    assert out["tier"] == "strong"
    assert out["broker_capacity"] is True


def test_cache_broker_only_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")
    from hw.cache import get_cached_profile
    import hw.cache as cache_mod

    cache_mod._broker_cached = None
    with patch(
        "broker_client.capacity_bridge.try_broker_probe_dict",
        return_value=None,
    ):
        with pytest.raises(RuntimeError, match=r"CAPACITY=1\|2"):
            get_cached_profile(fresh=True)


def test_fit_uses_broker_profile(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    from env import find_repo_root
    from hw.fit import rank_models

    local = profile_from_probe(
        {
            "tier": "weak",
            "ram_total_gb": 4.0,
            "ram_available_gb": 2.0,
            "cpu_count": 2,
            "gpus": [],
            "gpu_groups": [],
            "unified_memory": False,
            "errors": [],
            "platform": "test",
        }
    )
    broker_raw = {
        "tier": "strong",
        "ram_total_gb": 64.0,
        "ram_available_gb": 32.0,
        "cpu_count": 16,
        "gpus": [],
        "gpu_groups": [],
        "unified_memory": False,
        "errors": [],
        "platform": "broker_capacity",
        "broker_capacity": True,
    }
    with patch(
        "broker_client.capacity_bridge.try_broker_probe_dict",
        return_value=broker_raw,
    ):
        ranked = rank_models(find_repo_root(), local, limit=5)
    assert ranked
