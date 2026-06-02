from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agent_core.models import EventType
from nimbusware_api.app import app

pytestmark = pytest.mark.slow


def test_get_bundle_search_returns_hits(client: TestClient) -> None:
    r = client.get("/v1/bundles/search", params={"q": "auth", "k": 5})
    assert r.status_code == 200
    body = r.json()
    assert body.get("query") == "auth"
    assert body.get("k") == 5
    hits = body.get("hits") or []
    ids = {h.get("id") for h in hits if isinstance(h, dict)}
    assert "auth-rbac-starter" in ids


def test_get_bundle_search_echoes_default_k_when_omitted(client: TestClient) -> None:
    """``k`` defaults to 5 on the route; the response must echo that same default."""
    r = client.get("/v1/bundles/search", params={"q": "auth"})
    assert r.status_code == 200
    assert r.json().get("k") == 5


def test_get_bundle_search_echoes_custom_k(client: TestClient) -> None:
    """API echoes the bounded ``k`` from the request, mirroring the console payload."""
    r = client.get("/v1/bundles/search", params={"q": "auth", "k": 3})
    assert r.status_code == 200
    assert r.json().get("k") == 3


def test_get_bundle_search_openapi_documents_200_example(client: TestClient) -> None:
    spec = client.app.openapi()
    ok = (
        spec.get("paths", {})
        .get("/v1/bundles/search", {})
        .get("get", {})
        .get("responses", {})
        .get("200", {})
    )
    assert isinstance(ok, dict)
    ex = ok.get("content", {}).get("application/json", {}).get("example", {})
    assert ex.get("query") == "auth"
    assert ex.get("k") == 5
    assert isinstance(ex.get("hits"), list) and ex["hits"]
    assert ex["hits"][0].get("id") == "auth-rbac-starter"
    assert "faiss_index_ready" in ex
    assert isinstance(ex["faiss_index_ready"], bool)
    props = (
        spec.get("components", {})
        .get("schemas", {})
        .get("BundleSearchResponse", {})
        .get("properties", {})
    )
    assert "faiss_index_stale" in props


def test_get_bundle_search_reports_faiss_index_ready_bool(client: TestClient) -> None:
    """``faiss_index_ready`` / ``faiss_index_stale`` mirror on-disk FAISS sync helpers."""
    from hermes_extensions.catalog import (
        bundle_faiss_index_ready,
        bundle_faiss_index_sync_state,
    )

    r = client.get("/v1/bundles/search", params={"q": "auth", "k": 5})
    assert r.status_code == 200
    body = r.json()
    assert "faiss_index_ready" in body
    assert isinstance(body["faiss_index_ready"], bool)
    assert "faiss_index_stale" in body
    repo_root = Path(os.environ["NIMBUSWARE_REPO_ROOT"])
    assert body["faiss_index_ready"] is bundle_faiss_index_ready(repo_root)
    assert body["faiss_index_stale"] == bundle_faiss_index_sync_state(repo_root).get("stale")


def test_get_bundle_search_uses_db_materialized_catalog(client: TestClient) -> None:
    from nimbusware_api.deps import get_orchestrator

    class _Mat:
        use_db = True

        @staticmethod
        def get_bundle_catalog() -> dict[str, object]:
            return {
                "version": 1,
                "bundles": [
                    {"id": "db-only-bundle", "title": "DB Bundle", "tags": ["db", "catalog"]},
                ],
                "workflow_bundle_map": {"default": "db-only-bundle"},
            }

    class _Orch:
        def __init__(self, root: Path) -> None:
            self.repo_root = root
            self.config_materializer = _Mat()

    app.dependency_overrides[get_orchestrator] = lambda: _Orch(
        Path(os.environ["NIMBUSWARE_REPO_ROOT"])
    )
    try:
        r = client.get("/v1/bundles/search", params={"q": "db", "k": 5})
        assert r.status_code == 200
        body = r.json()
        ids = {h.get("id") for h in (body.get("hits") or []) if isinstance(h, dict)}
        assert "db-only-bundle" in ids
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)


def test_get_persona_shelves_returns_catalog(client: TestClient) -> None:
    r = client.get("/v1/personas")
    assert r.status_code == 200
    body = r.json()
    assert body.get("version") == 1
    ba = body.get("business_area") or []
    dr = body.get("development_role") or []
    ba_ids = {e.get("id") for e in ba if isinstance(e, dict)}
    dr_ids = {e.get("id") for e in dr if isinstance(e, dict)}
    assert "commerce" in ba_ids
    assert "backend_engineer" in dr_ids


def test_get_persona_shelves_openapi_documents_200_example(client: TestClient) -> None:
    spec = client.app.openapi()
    ok = (
        spec.get("paths", {})
        .get("/v1/personas", {})
        .get("get", {})
        .get("responses", {})
        .get("200", {})
    )
    assert isinstance(ok, dict)
    ex = ok.get("content", {}).get("application/json", {}).get("example", {})
    assert ex.get("version") == 1
    assert isinstance(ex.get("business_area"), list) and ex["business_area"]
    assert ex["business_area"][0].get("id") == "commerce"


def test_persona_edit_round_trip_through_event_store(tmp_path: Path) -> None:
    """fo127 #14-edit: PATCH a persona, verify GET reflects it AND audit event lands.

    Drives the full API surface — POST + PATCH + GET — against an isolated
    tmp shelves.yaml plus an InMemoryEventStore so we exercise the wiring end
    to end without touching the real repo.
    """
    import yaml as _yaml  # local import keeps test module imports tidy

    from hermes_store.memory import InMemoryEventStore
    from nimbusware_api.deps import get_orchestrator, get_store

    personas_dir = tmp_path / "configs" / "personas"
    personas_dir.mkdir(parents=True, exist_ok=True)
    (personas_dir / "shelves.yaml").write_text(
        _yaml.safe_dump(
            {
                "version": 1,
                "business_area": [{"id": "commerce", "display_name": "C", "version": 1}],
                "development_role": [{"id": "be", "display_name": "BE", "version": 1}],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    class _Orch:
        def __init__(self, root: Path) -> None:
            self.repo_root = root

    store = InMemoryEventStore()
    app.dependency_overrides[get_orchestrator] = lambda: _Orch(tmp_path)
    app.dependency_overrides[get_store] = lambda: store
    try:
        with TestClient(app) as c:
            patch_body = {
                "expected_version": 1,
                "instructions": "Refund policy required.",
                "actor": "alice",
            }
            r = c.patch(
                "/v1/personas/business_area/commerce",
                json=patch_body,
                headers={
                    "X-Nimbusware-Admin-Token": "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
                },
            )
            assert r.status_code == 200, r.text
            patched = next(e for e in r.json()["business_area"] if e["id"] == "commerce")
            assert patched["instructions"] == "Refund policy required."
            assert patched["version"] == 2

            g = c.get("/v1/personas")
            assert g.status_code == 200
            on_wire = next(e for e in g.json()["business_area"] if e["id"] == "commerce")
            assert on_wire["instructions"] == "Refund policy required."
            assert on_wire["version"] == 2
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)
        app.dependency_overrides.pop(get_store, None)

    persona_events = [
        r
        for r in store._rows  # type: ignore[attr-defined]
        if r.get("event_type") == EventType.PERSONA_SHELF_UPDATED.value
    ]
    assert len(persona_events) == 1
    ev = persona_events[0]
    assert ev["payload"]["persona_id"] == "commerce"
    assert ev["payload"]["prev_version"] == 1
    assert ev["payload"]["next_version"] == 2
    assert ev["payload"]["fields_changed"] == ["instructions"]
    assert ev["payload"]["actor"] == "alice"
