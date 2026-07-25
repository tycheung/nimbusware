from __future__ import annotations

import pytest

from broker_client import (
    BrokerDisabled,
    bind_egress_check,
    bind_research_fetch,
    broker_egress_enabled,
    broker_research_enabled,
    select_backend,
)
from executor.egress_bridge import try_broker_egress_check
from research.research_bridge import try_broker_research_fetch


def test_sak406_g_research_egress_dual_run_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_RESEARCH", raising=False)
    monkeypatch.delenv("NIMBUSWARE_BROKER_EGRESS", raising=False)

    assert broker_research_enabled() is False
    assert broker_egress_enabled() is False
    assert select_backend("research") == "python"
    assert select_backend("egress") == "python"
    assert try_broker_research_fetch("https://example.com") is None
    assert try_broker_egress_check("https://example.com") is None

    with pytest.raises(BrokerDisabled):
        bind_research_fetch()
    with pytest.raises(BrokerDisabled):
        bind_egress_check()

    monkeypatch.setenv("NIMBUSWARE_BROKER_RESEARCH", "1")
    monkeypatch.setenv("NIMBUSWARE_BROKER_EGRESS", "1")

    assert broker_research_enabled() is True
    assert broker_egress_enabled() is True
    assert select_backend("research") == "broker"
    assert select_backend("egress") == "broker"
