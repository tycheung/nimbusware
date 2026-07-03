from __future__ import annotations

from pathlib import Path

from config.export import (
    export_config_to_repo,
    export_provider_connections_metadata,
    list_store_documents,
)
from config.keys import KEY_USER_DEFAULTS, NS_MODEL_BINDINGS, NS_WORKFLOWS
from config.store import InMemoryConfigStore


def test_list_store_documents_respects_namespace_filter() -> None:
    store = InMemoryConfigStore()
    store.upsert(NS_MODEL_BINDINGS, KEY_USER_DEFAULTS, {"version": 1, "roles": {}})
    store.upsert(NS_WORKFLOWS, "micro_slice", {"version": 1})

    filtered = list_store_documents(store, namespaces={NS_MODEL_BINDINGS})
    assert filtered
    assert all(doc["namespace"] == NS_MODEL_BINDINGS for doc in filtered)


def test_export_model_bindings_and_list_documents(tmp_path: Path) -> None:
    store = InMemoryConfigStore()
    bindings = {"version": 1, "roles": {"planner": {"provider_id": "ollama", "model_id": "m"}}}
    store.upsert(NS_MODEL_BINDINGS, KEY_USER_DEFAULTS, bindings)
    store.upsert(NS_WORKFLOWS, "micro_slice", {"version": 1, "name": "micro_slice"})

    counts = export_config_to_repo(store, tmp_path, namespaces={NS_MODEL_BINDINGS, NS_WORKFLOWS})
    assert counts[NS_MODEL_BINDINGS] == 1
    assert counts[NS_WORKFLOWS] == 1
    assert (tmp_path / "configs" / "model_bindings" / "defaults.yaml").is_file()

    docs = list_store_documents(store)
    keys = {(d["namespace"], d["document_key"]) for d in docs}
    assert (NS_MODEL_BINDINGS, KEY_USER_DEFAULTS) in keys
    assert (NS_WORKFLOWS, "micro_slice") in keys


def test_export_provider_connections_metadata_empty(tmp_path: Path, monkeypatch) -> None:
    class _FakeStore:
        def __init__(self, _conninfo: str) -> None:
            pass

        def export_metadata_for_user(self, *, user_id: str = "") -> list[dict]:
            return []

    monkeypatch.setattr(
        "config.provider_connections.ProviderConnectionStore",
        _FakeStore,
    )
    assert export_provider_connections_metadata("postgresql://local/test", tmp_path) == 0
    assert (tmp_path / "configs" / "provider_connections" / "metadata.yaml").is_file()
