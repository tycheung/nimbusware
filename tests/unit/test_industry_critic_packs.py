from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_orchestrator.critic_pack_resolve import load_critic_pack

REPO = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("pack_id", "domain"),
    [
        ("fintech-api", "fintech"),
        ("healthcare-api", "healthcare"),
    ],
)
def test_industry_critic_packs_load(pack_id: str, domain: str) -> None:
    pack = load_critic_pack(REPO, pack_id)
    assert pack is not None
    assert pack.get("id") == pack_id
    assert pack.get("domain") == domain
    assert pack.get("blocking_authority") == "advisory"
    rules = pack.get("review_rules")
    assert isinstance(rules, list)
    assert len(rules) >= 3
