from __future__ import annotations

from pathlib import Path

from nimbusware_config.model_policy_store import (
    load_model_policy,
    policy_allows_cloud_provider,
    policy_allows_model,
    save_model_policy,
)


def test_load_model_policy_defaults(tmp_path: Path) -> None:
    doc = load_model_policy(tmp_path)
    assert doc["audit_include_binding_events"] is True
    assert policy_allows_cloud_provider(doc, "openai") is True
    assert policy_allows_model(doc, "gpt-4") is True


def test_model_policy_allowlists(tmp_path: Path) -> None:
    doc = {
        "version": 1,
        "allowed_cloud_providers": ["openai"],
        "blocked_model_ids": ["gpt-4"],
        "require_admin_for_cloud_swap": True,
        "audit_include_binding_events": True,
    }
    save_model_policy(tmp_path, doc)
    loaded = load_model_policy(tmp_path)
    assert policy_allows_cloud_provider(loaded, "openai") is True
    assert policy_allows_cloud_provider(loaded, "anthropic") is False
    assert policy_allows_model(loaded, "gpt-4") is False
    assert policy_allows_model(loaded, "gpt-4o-mini") is True
