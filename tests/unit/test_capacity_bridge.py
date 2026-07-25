from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from broker_client import (
    BrokerDisabled,
    bind_capacity_probe,
    capacity_probe_via_broker,
    try_broker_capacity_probe,
)
import broker_client.capacity_bridge as bridge_mod


def test_bind_capacity_probe_returns_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    plan = bind_capacity_probe()
    assert plan["offer"] == "capacity.probe"
    assert plan["transport"] == "http"
    assert "bind" in plan["steps"]


def test_bind_capacity_probe_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_CAPACITY", raising=False)
    with pytest.raises(BrokerDisabled):
        bind_capacity_probe()


def test_capacity_probe_via_broker_uses_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    mock_http = MagicMock()
    mock_http.capacity.return_value = {"tier": "medium", "cpus": 8}
    out = capacity_probe_via_broker(client=mock_http)
    mock_http.capacity.assert_called_once_with()
    assert out == {"tier": "medium", "cpus": 8}


def test_try_broker_capacity_probe_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_CAPACITY", raising=False)
    assert try_broker_capacity_probe() is None


def test_try_broker_capacity_probe_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    monkeypatch.setattr(
        bridge_mod,
        "capacity_probe_via_broker",
        lambda client=None: {"tier": "strong"},
    )
    assert try_broker_capacity_probe() == {"tier": "strong"}


def test_try_broker_capacity_probe_peel_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak435-a: under CAPACITY=1, bridge re-raises (no None soft miss)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")

    def _boom() -> dict:
        raise RuntimeError("down")

    monkeypatch.setattr(bridge_mod, "capacity_probe_via_broker", _boom)
    with pytest.raises(RuntimeError, match="down"):
        try_broker_capacity_probe()


def test_try_broker_capacity_probe_broker_only_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "2")

    def _boom() -> dict:
        raise RuntimeError("down")

    monkeypatch.setattr(bridge_mod, "capacity_probe_via_broker", _boom)
    with pytest.raises(RuntimeError, match="down"):
        try_broker_capacity_probe()


def test_pressure_from_capacity_probe_levels() -> None:
    from broker_client.stage_bind.capacity import pressure_from_capacity_probe

    level, details = pressure_from_capacity_probe(
        {
            "snapshot": {
                "total_ram_mb": 10_000,
                "available_ram_mb": 1_000,
                "cpu_usage_pct": 10.0,
            }
        },
        max_system_ram_pct=75.0,
    )
    assert level == "block"
    assert details["reason"] == "ram_over_cap"


def test_parallel_writer_stages_from_capacity() -> None:
    from broker_client.stage_bind.capacity import parallel_writer_stages_from_capacity

    assert (
        parallel_writer_stages_from_capacity({"max_parallel_writer_stages": 3}) == 3
    )
    derived = parallel_writer_stages_from_capacity(
        {"snapshot": {"total_ram_mb": 32_768, "cpu_logical": 8}}
    )
    assert derived == 3


def test_bind_capacity_pressure_and_fit(monkeypatch: pytest.MonkeyPatch) -> None:
    from broker_client import bind_capacity_fit, bind_capacity_pressure

    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    assert bind_capacity_pressure()["offer"] == "capacity.pressure"
    assert bind_capacity_fit()["offer"] == "capacity.fit"


def test_try_broker_capacity_pressure_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    from broker_client import try_broker_capacity_pressure

    monkeypatch.delenv("NIMBUSWARE_BROKER_CAPACITY", raising=False)
    assert try_broker_capacity_pressure() is None


def test_try_broker_parallel_writer_stages(monkeypatch: pytest.MonkeyPatch) -> None:
    from broker_client import try_broker_parallel_writer_stages

    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    monkeypatch.setattr(
        bridge_mod,
        "capacity_probe_via_broker",
        lambda client=None: {"max_parallel_writer_stages": 2},
    )
    assert try_broker_parallel_writer_stages() == 2


def test_probe_dict_from_capacity() -> None:
    from broker_client.stage_bind.capacity import probe_dict_from_capacity

    raw = probe_dict_from_capacity(
        {
            "snapshot": {
                "total_ram_mb": 16_384,
                "available_ram_mb": 8_192,
                "cpu_logical": 8,
                "source": "fake",
            }
        }
    )
    assert raw["tier"] == "medium"
    assert raw["ram_total_gb"] == 16.0
    assert raw["broker_capacity"] is True


def test_try_broker_probe_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    from broker_client import try_broker_probe_dict

    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    monkeypatch.setattr(
        bridge_mod,
        "capacity_probe_via_broker",
        lambda client=None: {
            "snapshot": {
                "total_ram_mb": 32_768,
                "available_ram_mb": 16_384,
                "cpu_logical": 16,
                "source": "fake",
            }
        },
    )
    out = try_broker_probe_dict()
    assert out is not None
    assert out["tier"] == "strong"


def test_compute_work_via_broker_http_first(monkeypatch: pytest.MonkeyPatch) -> None:
    from broker_client.stage_bind.compute import compute_work_via_broker
    from unittest.mock import MagicMock

    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    monkeypatch.setenv("NIMBUSWARE_BROKER_HTTP", "http://127.0.0.1:8787")
    mock_http = MagicMock()
    mock_http.compute_work.return_value = {"work": {"id": "w1"}, "action": "enqueue"}
    out = compute_work_via_broker(
        {"action": "enqueue", "kind": "echo", "payload": {}},
        http=mock_http,
    )
    mock_http.compute_work.assert_called_once()
    assert out["work"]["id"] == "w1"


def test_bind_compute_work_prefers_http_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    from broker_client.stage_bind.compute import bind_compute_work

    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    monkeypatch.setenv("NIMBUSWARE_BROKER_HTTP", "http://127.0.0.1:8787")
    plan = bind_compute_work()
    assert plan["transport"] == "http"


def test_governor_metadata_from_capacity() -> None:
    from broker_client.stage_bind.capacity import governor_metadata_from_capacity

    meta = governor_metadata_from_capacity(
        {
            "snapshot": {
                "total_ram_mb": 32_768,
                "available_ram_mb": 16_384,
                "cpu_logical": 8,
                "source": "fake",
            }
        }
    )
    assert meta["hardware_tier"] == "strong"
    assert meta["max_parallel_writer_stages"] == 3
    assert meta["capacity_source"] == "broker"


def test_governor_from_metadata_tolerates_broker_snapshot() -> None:
    from hw.governor import governor_from_metadata

    gov = governor_from_metadata(
        {
            "snapshot": {
                "total_ram_mb": 16_384,
                "available_ram_mb": 8_192,
                "cpu_logical": 8,
            }
        }
    )
    assert gov is not None
    assert gov.hardware_tier == "medium"
    assert gov.max_parallel_writer_stages == 2
