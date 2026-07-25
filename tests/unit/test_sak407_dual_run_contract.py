from __future__ import annotations

import pytest

from broker_client import (
    BrokerDisabled,
    bind_compute_work,
    broker_compute_enabled,
    select_backend,
    try_broker_compute_work,
)


def test_sak407_e_compute_dual_run_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_COMPUTE", raising=False)

    assert broker_compute_enabled() is False
    assert select_backend("compute") == "python"
    assert try_broker_compute_work({"kind": "echo"}) is None

    with pytest.raises(BrokerDisabled):
        bind_compute_work()

    monkeypatch.setenv("NIMBUSWARE_BROKER_COMPUTE", "1")

    assert broker_compute_enabled() is True
    assert select_backend("compute") == "broker"
