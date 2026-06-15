from __future__ import annotations

import pytest

from nimbusware_config.keys import KEY_MODEL_ROUTING, NS_POLICY
from nimbusware_config.notify import get_config_notify_hub
from nimbusware_config.store import InMemoryConfigStore


@pytest.mark.integration
def test_config_store_upsert_publishes_notify_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("nimbusware_config.config_notify_enabled", lambda: True)
    store = InMemoryConfigStore()
    hub = get_config_notify_hub()
    before = hub.delivery_count
    store.upsert(
        NS_POLICY,
        KEY_MODEL_ROUTING,
        {"runtime": {"base_url": "http://127.0.0.1:11434"}},
    )
    assert hub.delivery_count >= before + 1
    assert hub.last_event is not None
    assert hub.last_event.document_key == KEY_MODEL_ROUTING
