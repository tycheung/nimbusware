from __future__ import annotations

from unittest.mock import patch

import pytest

from orchestrator.workflow.parallel_writers import max_parallel_writer_stages_from_governor


def test_max_parallel_prefers_broker_capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    with patch(
        "broker_client.capacity_bridge.try_broker_parallel_writer_stages",
        return_value=3,
    ):
        assert max_parallel_writer_stages_from_governor() == 3


def test_max_parallel_falls_back_to_hw_when_broker_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_CAPACITY", raising=False)
    with (
        patch(
            "broker_client.capacity_bridge.try_broker_parallel_writer_stages",
            return_value=None,
        ),
        patch(
            "broker_client.capacity_bridge.try_broker_capacity_probe",
            return_value=None,
        ),
        patch(
            "hw.pressure.sample_pressure",
            return_value=("ok", {"tier": "medium"}),
        ),
        patch(
            "hw.governor.governor_for_profile",
            return_value=type(
                "G",
                (),
                {"max_parallel_writer_stages": 2},
            )(),
        ),
        patch("hw.cache.get_cached_profile", return_value=object()),
        patch("hw.pressure.pressure_limits_parallel", return_value=2),
    ):
        assert max_parallel_writer_stages_from_governor() == 2


def test_max_parallel_refuses_local_under_capacity_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_CAPACITY", "1")
    with (
        patch(
            "broker_client.capacity_bridge.try_broker_parallel_writer_stages",
            return_value=None,
        ),
        patch(
            "broker_client.capacity_bridge.try_broker_capacity_probe",
            return_value=None,
        ),
    ):
        with pytest.raises(RuntimeError, match=r"CAPACITY=1\|2"):
            max_parallel_writer_stages_from_governor()
