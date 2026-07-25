from __future__ import annotations

from unittest.mock import patch

import pytest

from broker_client import broker_compute_enabled
from orchestrator.compute_broker_bridge import try_broker_compute_work


def test_sak407_h_flag_off_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_COMPUTE", raising=False)
    assert broker_compute_enabled() is False
    assert try_broker_compute_work({"kind": "echo"}) is None


def test_sak407_h_delegates_to_broker_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")
    expected = {"status": "ok", "output": "hi"}

    with patch(
        "orchestrator.compute_broker_bridge._broker_compute_work",
        return_value=expected,
    ) as mock_bridge:
        out = try_broker_compute_work({"kind": "echo", "input": "hi"})

    mock_bridge.assert_called_once_with({"kind": "echo", "input": "hi"})
    assert out == expected


def test_sak407_h_peel_propagates_broker_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak435-a: orchestrator bridge re-raises under COMPUTE=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")

    with patch(
        "orchestrator.compute_broker_bridge._broker_compute_work",
        side_effect=RuntimeError("broker down"),
    ):
        with pytest.raises(RuntimeError, match="broker down"):
            try_broker_compute_work({"kind": "echo"})


def test_orchestrator_package_lazy_exports_compute_bridge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """refactor:orchestrator-compute-bridge-export — lazy import avoids cycles."""
    import orchestrator

    monkeypatch.delenv("NIMBUSWARE_BROKER_COMPUTE", raising=False)
    fn = orchestrator.try_broker_compute_work
    assert callable(fn)
    assert fn({"kind": "echo"}) is None
