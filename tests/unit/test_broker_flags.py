from __future__ import annotations

import pytest

from broker_client import (
    broker_capacity_enabled,
    broker_capacity_only,
    broker_compute_enabled,
    broker_compute_only,
    broker_egress_enabled,
    broker_egress_only,
    broker_llm_enabled,
    broker_llm_only,
    broker_memory_enabled,
    broker_memory_only,
    broker_mcp_enabled,
    broker_only,
    broker_research_enabled,
    broker_research_only,
    broker_sandbox_enabled,
    broker_sandbox_only,
    broker_tools_enabled,
    broker_tools_only,
    mcp_configured,
    select_backend,
    select_llm_backend,
)
from broker_client.flags import _env_mode


@pytest.mark.parametrize(
    ("env", "checker", "only_checker"),
    [
        ("NIMBUSWARE_BROKER_LLM", broker_llm_enabled, broker_llm_only),
        ("NIMBUSWARE_BROKER_SANDBOX", broker_sandbox_enabled, broker_sandbox_only),
        ("NIMBUSWARE_BROKER_TOOLS", broker_tools_enabled, broker_tools_only),
        ("NIMBUSWARE_BROKER_MEMORY", broker_memory_enabled, broker_memory_only),
        ("NIMBUSWARE_BROKER_RESEARCH", broker_research_enabled, broker_research_only),
        ("NIMBUSWARE_BROKER_EGRESS", broker_egress_enabled, broker_egress_only),
        ("NIMBUSWARE_BROKER_COMPUTE", broker_compute_enabled, broker_compute_only),
        ("NIMBUSWARE_BROKER_CAPACITY", broker_capacity_enabled, broker_capacity_only),
    ],
)
@pytest.mark.parametrize(
    ("value", "enabled", "only"),
    [
        ("1", True, False),
        ("true", True, False),
        ("TRUE", True, False),
        ("yes", True, False),
        ("2", True, True),
        ("broker-only", True, True),
        ("0", False, False),
        ("false", False, False),
        ("", False, False),
    ],
)
def test_domain_flags_mode_0_1_2(
    monkeypatch: pytest.MonkeyPatch,
    env: str,
    checker,
    only_checker,
    value: str,
    enabled: bool,
    only: bool,
) -> None:
    if value:
        monkeypatch.setenv(env, value)
    else:
        monkeypatch.delenv(env, raising=False)
    assert checker() is enabled
    assert only_checker() is only


def test_env_mode_returns_0_1_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    assert _env_mode("NIMBUSWARE_BROKER_LLM") == 0
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    assert _env_mode("NIMBUSWARE_BROKER_LLM") == 1
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    assert _env_mode("NIMBUSWARE_BROKER_LLM") == 2


def test_broker_only_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    assert broker_only("llm") is False
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    assert broker_only("llm") is True
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    assert broker_only("llm") is False


def test_broker_mcp_enabled_non_empty_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_MCP", raising=False)
    assert broker_mcp_enabled() is False
    assert mcp_configured() is False
    monkeypatch.setenv("NIMBUSWARE_BROKER_MCP", "http://127.0.0.1:8080/mcp")
    assert broker_mcp_enabled() is True
    assert mcp_configured() is True


def test_select_llm_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_BROKER_LLM", raising=False)
    assert select_llm_backend() == "python"
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    assert select_llm_backend() == "broker"
    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "2")
    assert select_llm_backend() == "broker"


@pytest.mark.parametrize(
    ("domain", "env"),
    [
        ("llm", "NIMBUSWARE_BROKER_LLM"),
        ("sandbox", "NIMBUSWARE_BROKER_SANDBOX"),
        ("tools", "NIMBUSWARE_BROKER_TOOLS"),
        ("memory", "NIMBUSWARE_BROKER_MEMORY"),
        ("research", "NIMBUSWARE_BROKER_RESEARCH"),
        ("egress", "NIMBUSWARE_BROKER_EGRESS"),
        ("compute", "NIMBUSWARE_BROKER_COMPUTE"),
        ("capacity", "NIMBUSWARE_BROKER_CAPACITY"),
    ],
)
def test_select_backend(
    monkeypatch: pytest.MonkeyPatch,
    domain: str,
    env: str,
) -> None:
    monkeypatch.delenv(env, raising=False)
    assert select_backend(domain) == "python"
    monkeypatch.setenv(env, "1")
    assert select_backend(domain) == "broker"
    monkeypatch.setenv(env, "2")
    assert select_backend(domain) == "broker"


def test_select_backend_unknown_domain() -> None:
    with pytest.raises(ValueError, match="unknown peel domain"):
        select_backend("unknown")
