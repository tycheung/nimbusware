from __future__ import annotations

from nimbusware_env.env_flags import nimbusware_integration_adapter_live_enabled


def test_integration_adapter_live_default_off(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_INTEGRATION_ADAPTER_LIVE", raising=False)
    assert nimbusware_integration_adapter_live_enabled() is False


def test_integration_adapter_live_on(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_INTEGRATION_ADAPTER_LIVE", "1")
    assert nimbusware_integration_adapter_live_enabled() is True
