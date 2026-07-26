from __future__ import annotations

import pytest

from broker_client import BrokerDisabled, bind_plan, list_bind_domains
from broker_client.stage_bind.registry import DOMAIN_BINDS

_DOMAIN_FLAGS: dict[str, str] = {
    "llm": "NIMBUSWARE_BROKER_LLM",
    "sandbox": "NIMBUSWARE_BROKER_SANDBOX",
    "tools": "NIMBUSWARE_BROKER_TOOLS",
    "memory": "NIMBUSWARE_BROKER_MEMORY",
    "research": "NIMBUSWARE_BROKER_RESEARCH",
    "egress": "NIMBUSWARE_BROKER_EGRESS",
    "compute": "NIMBUSWARE_BROKER_COMPUTE",
    "capacity": "NIMBUSWARE_BROKER_CAPACITY",
}

_DOMAIN_OFFERS: dict[str, str] = {
    "llm": "llm.chat",
    "sandbox": "sandbox.exec",
    "tools": "tools.shell",
    "memory": "memory.search",
    "research": "research.fetch",
    "egress": "network.egress.check",
    "compute": "compute.work",
    "capacity": "capacity.probe",
}


@pytest.mark.parametrize("domain", sorted(DOMAIN_BINDS.keys()))
def test_bind_plan_returns_plan_when_flag_enabled(
    monkeypatch: pytest.MonkeyPatch,
    domain: str,
) -> None:
    monkeypatch.setenv(_DOMAIN_FLAGS[domain], "1")
    plan = bind_plan(domain)
    assert plan["offer"] == _DOMAIN_OFFERS[domain]
    assert "bind" in plan["steps"]


@pytest.mark.parametrize("domain", sorted(DOMAIN_BINDS.keys()))
def test_bind_plan_disabled_raises(
    monkeypatch: pytest.MonkeyPatch,
    domain: str,
) -> None:
    monkeypatch.delenv(_DOMAIN_FLAGS[domain], raising=False)
    with pytest.raises(BrokerDisabled):
        bind_plan(domain)


def test_bind_plan_unknown_domain_raises() -> None:
    with pytest.raises(ValueError, match="unknown peel domain"):
        bind_plan("widgets")


def test_list_bind_domains_matches_registry() -> None:
    assert list_bind_domains() == sorted(DOMAIN_BINDS.keys())
