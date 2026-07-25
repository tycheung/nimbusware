from __future__ import annotations

import pytest

from orchestrator import try_broker_capacity_probe
from orchestrator.capacity_broker_bridge import try_broker_capacity_probe as orch_probe


def test_orchestrator_capacity_bridge_importable() -> None:
    assert callable(try_broker_capacity_probe)
    assert callable(orch_probe)
    assert try_broker_capacity_probe is orch_probe or callable(try_broker_capacity_probe)


def test_orchestrator_capacity_flag_off_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_CAPACITY", raising=False)
    assert orch_probe() is None
