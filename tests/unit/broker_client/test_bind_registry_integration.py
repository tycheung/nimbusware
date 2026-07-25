from __future__ import annotations

from broker_client import bind_plan, list_bind_domains


def test_list_bind_domains_returns_all_eight_and_llm_bind_plan(
    monkeypatch,
) -> None:
    domains = list_bind_domains()
    assert domains == sorted(
        [
            "capacity",
            "compute",
            "egress",
            "llm",
            "memory",
            "research",
            "sandbox",
            "tools",
        ]
    )
    assert len(domains) == 8

    monkeypatch.setenv("NIMBUSWARE_BROKER_LLM", "1")
    plan = bind_plan("llm")
    assert plan["offer"] == "llm.chat"
    assert "bind" in plan["steps"]
