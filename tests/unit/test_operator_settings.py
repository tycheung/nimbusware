from __future__ import annotations

import os

import pytest

from nimbusware_config.store import InMemoryConfigStore
from nimbusware_env.settings_catalog import (
    CATALOG,
    KEY_USER,
    NS_OPERATOR_SETTINGS,
    SettingScope,
)
from nimbusware_env.settings_resolve import (
    refresh_scope_caches,
    resolve_bool,
    resolve_raw,
    set_run_operator_settings,
)
from nimbusware_env.settings_store import (
    apply_scope_to_environ,
    merge_scope_values,
    validate_patch,
)


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    import nimbusware_env.settings_resolve as mod

    mod._user_cache = None
    mod._system_cache = None
    yield
    mod._user_cache = None
    mod._system_cache = None


def test_catalog_covers_managed_keys() -> None:
    assert "HERMES_RERESARCH_MISSING_CONTEXT" in CATALOG
    assert CATALOG["HERMES_RERESARCH_MISSING_CONTEXT"].scope == SettingScope.SYSTEM
    assert CATALOG["NIMBUSWARE_DATABASE_URL"].scope == SettingScope.INSTALL
    assert len(CATALOG) >= 100


def test_validate_patch_bool_coercion() -> None:
    out = validate_patch(
        {"HERMES_USE_LLM": "yes"},
        scope=SettingScope.USER,
        admin=False,
    )
    assert out["HERMES_USE_LLM"] == "1"


def test_resolve_precedence_user_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_USE_LLM", "0")
    store = InMemoryConfigStore()
    store.upsert(
        NS_OPERATOR_SETTINGS,
        KEY_USER,
        {"values": {"HERMES_USE_LLM": "1"}},
    )
    monkeypatch.setattr(
        "nimbusware_env.settings_store._load_store",
        lambda: store,
    )
    refresh_scope_caches()
    assert resolve_bool("HERMES_USE_LLM", default=False) is True


def test_resolve_run_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERMES_MICRO_SLICE_COUNT", raising=False)
    token = set_run_operator_settings({"HERMES_MICRO_SLICE_COUNT": "5"})
    try:
        from nimbusware_env.settings_resolve import resolve_int

        assert resolve_int("HERMES_MICRO_SLICE_COUNT", default=2) == 5
    finally:
        from nimbusware_env.settings_resolve import reset_run_operator_settings

        reset_run_operator_settings(token)


def test_merge_system_applies_to_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    store = InMemoryConfigStore()
    monkeypatch.setattr(
        "nimbusware_env.settings_store._load_store",
        lambda: store,
    )
    key = "HERMES_RERESARCH_MISSING_CONTEXT"
    try:
        merge_scope_values(
            SettingScope.SYSTEM,
            {key: "1"},
            admin=True,
        )
        apply_scope_to_environ(SettingScope.SYSTEM)
        assert os.environ.get(key) == "1"
        refresh_scope_caches()
        assert resolve_raw(key) == "1"
    finally:
        os.environ.pop(key, None)


def test_env_over_yaml_resolved_after_postgres_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nimbusware_env.settings_resolve import env_over_yaml_resolved

    key = "HERMES_STUB_IMPLEMENTATION_CRITICS"
    monkeypatch.delenv(key, raising=False)
    store = InMemoryConfigStore()
    monkeypatch.setattr(
        "nimbusware_env.settings_store._load_store",
        lambda: store,
    )
    try:
        merge_scope_values(SettingScope.SYSTEM, {key: "1"}, admin=True)
        apply_scope_to_environ(SettingScope.SYSTEM)
        assert env_over_yaml_resolved(key, False) is True
    finally:
        os.environ.pop(key, None)
