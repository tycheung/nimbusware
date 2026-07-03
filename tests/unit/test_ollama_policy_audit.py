from __future__ import annotations

from orchestrator.ollama_user_policy import merge_policy_into_routing


def test_policy_merge_stamps_updated_at() -> None:
    merged = merge_policy_into_routing({}, allow_delete=True)
    stamp = merged["ollama_user_policy"].get("updated_at")
    assert isinstance(stamp, str)
    assert stamp.endswith("+00:00") or "T" in stamp
