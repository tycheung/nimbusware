from __future__ import annotations

import pytest

from nimbusware_store.retention_policy import purge_blocked_by_legal_hold, tenant_legal_hold_enabled


def test_tenant_legal_hold_false_without_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_EVENT_STORE_LEGAL_HOLD", raising=False)
    assert tenant_legal_hold_enabled("default") is False
    assert purge_blocked_by_legal_hold("default") is False


def test_env_legal_hold_blocks_purge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_EVENT_STORE_LEGAL_HOLD", "1")
    assert purge_blocked_by_legal_hold("default") is True


def test_tenant_audit_policy_blocks_purge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_EVENT_STORE_LEGAL_HOLD", raising=False)
    monkeypatch.setenv("NIMBUSWARE_DATABASE_URL", "postgresql://unused")

    class _Row:
        content = {"version": 1, "legal_hold": True, "redaction_patterns": []}

    class _Store:
        def get(self, namespace: str, key: str) -> _Row | None:
            return _Row()

    monkeypatch.setattr(
        "nimbusware_config.tenant_policy_store.PostgresConfigStore",
        lambda _url: _Store(),
    )
    assert tenant_legal_hold_enabled("acme") is True
    assert purge_blocked_by_legal_hold("acme") is True
