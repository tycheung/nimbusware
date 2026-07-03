from __future__ import annotations

from pathlib import Path

import pytest

from config.keys import KEY_USER_DEFAULTS, NS_MODEL_BINDINGS
from config.model_bindings_store import (
    list_binding_role_catalog,
    load_defaults_file,
    load_user_defaults,
    merge_role_bindings,
    save_user_defaults,
)
from config.store import InMemoryConfigStore

REPO = Path(__file__).resolve().parents[2]


def test_load_defaults_file_missing_returns_empty(tmp_path: Path) -> None:
    assert load_defaults_file(tmp_path) == {"version": 1, "roles": {}}


def test_load_defaults_file() -> None:
    doc = load_defaults_file(REPO)
    assert doc.get("version") == 1
    assert "planner" in (doc.get("roles") or {})


def test_role_catalog_includes_planner() -> None:
    roles = list_binding_role_catalog(REPO)
    assert any(r["agent_role"] == "planner" for r in roles)


def test_load_user_defaults_from_store() -> None:
    store = InMemoryConfigStore()
    store.upsert(
        NS_MODEL_BINDINGS,
        KEY_USER_DEFAULTS,
        {"version": 1, "roles": {"planner": {"provider_id": "ollama", "model_id": "m"}}},
    )
    doc = load_user_defaults(REPO, store=store)
    assert doc["roles"]["planner"]["model_id"] == "m"


def test_save_user_defaults_writes_file(tmp_path: Path) -> None:
    doc = {
        "version": 1,
        "roles": {"planner": {"provider_kind": "local", "provider_id": "ollama", "model_id": "x"}},
    }
    saved = save_user_defaults(tmp_path, doc)
    assert saved["roles"]["planner"]["model_id"] == "x"
    assert load_defaults_file(tmp_path)["roles"]["planner"]["model_id"] == "x"


def test_save_user_defaults_rejects_invalid_roles(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="roles must be an object"):
        save_user_defaults(tmp_path, {"version": 1, "roles": "bad"})


def test_save_user_defaults_upserts_config_store(tmp_path: Path) -> None:
    store = InMemoryConfigStore()
    doc = {"roles": {"planner": {"provider_id": "ollama", "model_id": "m"}}}
    save_user_defaults(tmp_path, doc, store=store)
    row = store.get(NS_MODEL_BINDINGS, KEY_USER_DEFAULTS)
    assert row is not None
    assert row.content["roles"]["planner"]["model_id"] == "m"


def test_merge_role_bindings_includes_catalog_and_extra_roles(tmp_path: Path) -> None:
    store = InMemoryConfigStore()
    store.upsert(
        NS_MODEL_BINDINGS,
        KEY_USER_DEFAULTS,
        {
            "version": 1,
            "roles": {
                "planner": {"provider_id": "ollama", "model_id": "bound"},
                "extra_role": {"provider_id": "openai", "model_id": "gpt"},
            },
        },
    )
    merged = merge_role_bindings(REPO, store=store)
    by_role = {row["agent_role"]: row for row in merged}
    assert by_role["planner"]["binding"]["model_id"] == "bound"
    assert by_role["extra_role"]["binding"]["model_id"] == "gpt"
