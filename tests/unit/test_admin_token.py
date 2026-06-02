from __future__ import annotations

import pytest

from nimbusware_env.admin_token import (
    DEFAULT_NIMBUSWARE_ADMIN_TOKEN,
    apply_default_admin_token_env,
    is_loopback_host,
    nimbusware_admin_token,
    require_non_default_admin_token_for_host,
    using_default_admin_token,
)


def test_default_admin_token_constant_is_unique() -> None:
    assert "SEARCH_AND_REPLACE_BEFORE_PROD" in DEFAULT_NIMBUSWARE_ADMIN_TOKEN


def test_nimbusware_admin_token_uses_env(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "custom-admin-secret")
    assert nimbusware_admin_token() == "custom-admin-secret"


def test_apply_default_admin_token_env(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_ADMIN_TOKEN", raising=False)
    apply_default_admin_token_env()
    assert nimbusware_admin_token() == DEFAULT_NIMBUSWARE_ADMIN_TOKEN


def test_using_default_admin_token(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_ADMIN_TOKEN", raising=False)
    assert using_default_admin_token() is True
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "custom-admin-secret")
    assert using_default_admin_token() is False


def test_require_non_default_admin_token_for_host(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_ADMIN_TOKEN", raising=False)
    require_non_default_admin_token_for_host("127.0.0.1")
    with pytest.raises(RuntimeError, match="dev default"):
        require_non_default_admin_token_for_host("0.0.0.0")


def test_is_loopback_host() -> None:
    assert is_loopback_host("127.0.0.1")
    assert is_loopback_host("127.2.3.4")
    assert is_loopback_host("localhost")
    assert is_loopback_host("::1")
    assert not is_loopback_host("0.0.0.0")
