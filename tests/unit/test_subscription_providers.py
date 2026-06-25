from __future__ import annotations

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.provider_registry import (
    load_subscription_provider_presets,
    subscription_preset_by_id,
)

ROOT = find_repo_root()


def test_subscription_provider_presets_include_desktop_apps() -> None:
    presets = load_subscription_provider_presets(ROOT)
    ids = {p["id"] for p in presets}
    assert "chatgpt_plus" in ids
    assert "claude_pro" in ids
    chatgpt = subscription_preset_by_id(ROOT, "chatgpt_plus")
    assert chatgpt is not None
    assert chatgpt["connection_kind"] == "subscription"
    assert chatgpt.get("desktop_app") == "ChatGPT"
    oauth = chatgpt.get("oauth")
    assert isinstance(oauth, dict)
    assert "offline_access" in str(oauth.get("scopes"))
