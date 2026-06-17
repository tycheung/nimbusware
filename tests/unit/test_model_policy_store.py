from __future__ import annotations

from pathlib import Path

from nimbusware_config.model_policy_store import (
    load_model_policy,
    policy_allows_cloud_provider,
    policy_allows_model,
    save_model_policy,
)


def test_model_policy_round_trip(tmp_path: Path) -> None:
    save_model_policy(
        tmp_path,
        {
            "version": 1,
            "allowed_cloud_providers": ["openai"],
            "blocked_model_ids": ["bad-model"],
        },
    )
    policy = load_model_policy(tmp_path)
    assert policy_allows_cloud_provider(policy, "openai")
    assert not policy_allows_cloud_provider(policy, "anthropic")
    assert not policy_allows_model(policy, "bad-model")
    assert policy_allows_model(policy, "gpt-4o-mini")
