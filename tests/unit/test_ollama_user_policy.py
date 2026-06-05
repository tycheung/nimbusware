from __future__ import annotations

import pytest

from nimbusware_orchestrator.ollama_user_policy import (
    OllamaUserPolicy,
    assert_user_may,
    merge_policy_into_routing,
    policy_from_routing,
)


def test_policy_defaults() -> None:
    assert policy_from_routing({}) == OllamaUserPolicy()


def test_merge_policy_into_routing() -> None:
    merged = merge_policy_into_routing({}, allow_pull=True)
    assert merged["ollama_user_policy"]["allow_pull"] is True
    assert merged["ollama_user_policy"]["allow_delete"] is False
    assert "updated_at" in merged["ollama_user_policy"]


def test_assert_user_may_blocks() -> None:
    policy = OllamaUserPolicy()
    with pytest.raises(PermissionError):
        assert_user_may(policy, "pull")
