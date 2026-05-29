"""Integration tests for fo127 persona write API (§14 #14-edit).

Fourteen axes split across all four HTTP verbs + cross-cutting validation:
POST happy / duplicate-409 / idempotency replay / 422 length-cap,
PATCH happy / 409 version-skew / 422 length-cap / empty-patch,
PUT happy / 404, DELETE happy / 409, unknown shelf 422, reserved persona_id 422,
and read-after-write through ``GET /v1/personas``.

All cases run against an in-memory store and a tmp-path shelves.yaml so the real
repo's persona catalog is never touched.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import yaml
from fastapi.testclient import TestClient

os.environ.setdefault("HERMES_REPO_ROOT", str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("HERMES_SKIP_PREFLIGHT", "1")
os.environ.setdefault("HERMES_ADMIN_TOKEN", "test-admin-token")

from agent_core.models import EventType  # noqa: E402
from hermes_api.app import app  # noqa: E402
from hermes_api.deps import get_orchestrator, get_store  # noqa: E402
from hermes_extensions.personas import PERSONA_INSTRUCTIONS_MAX_CHARS  # noqa: E402
from hermes_store.memory import InMemoryEventStore  # noqa: E402

ADMIN_HEADERS = {"X-Hermes-Admin-Token": "test-admin-token"}

INITIAL_SHELVES: dict = {
    "version": 1,
    "business_area": [
        {"id": "commerce", "display_name": "Commerce", "version": 1},
    ],
    "development_role": [
        {"id": "backend", "display_name": "Backend", "version": 1},
    ],
}


class _OrchStub:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Seed a tmp shelves.yaml + matching repo dir for the route's repo_root."""
    personas_dir = tmp_path / "configs" / "personas"
    personas_dir.mkdir(parents=True, exist_ok=True)
    (personas_dir / "shelves.yaml").write_text(
        yaml.safe_dump(INITIAL_SHELVES, sort_keys=False),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def in_memory_store() -> InMemoryEventStore:
    return InMemoryEventStore()


@pytest.fixture
def client(fake_repo: Path, in_memory_store: InMemoryEventStore) -> Iterator[TestClient]:
    stub = _OrchStub(repo_root=fake_repo)
    app.dependency_overrides[get_orchestrator] = lambda: stub
    app.dependency_overrides[get_store] = lambda: in_memory_store
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_orchestrator, None)
        app.dependency_overrides.pop(get_store, None)


def _read_disk(fake_repo: Path) -> dict:
    return yaml.safe_load(
        (fake_repo / "configs" / "personas" / "shelves.yaml").read_text(encoding="utf-8"),
    )


def _persona_events(store: InMemoryEventStore) -> list[dict[str, Any]]:
    return [
        e
        for e in store._rows  # type: ignore[attr-defined]
        if e.get("event_type") == EventType.PERSONA_SHELF_UPDATED.value
    ]


# ---------------------------------------------------------------------------
# Axis 1: POST happy path — new persona shows up + audit event recorded
# ---------------------------------------------------------------------------


def test_post_creates_new_persona_and_emits_audit_event(
    client: TestClient,
    fake_repo: Path,
    in_memory_store: InMemoryEventStore,
) -> None:
    body = {
        "entry": {
            "id": "ops",
            "display_name": "Ops",
            "instructions": "Reliability oversight.",
            "probation_status": "probation",
        },
        "actor": "alice",
    }
    r = client.post("/v1/personas/business_area", json=body, headers=ADMIN_HEADERS)
    assert r.status_code == 201, r.text
    catalog = r.json()
    new = next(e for e in catalog["business_area"] if e["id"] == "ops")
    assert new["version"] == 1
    assert new["instructions"] == "Reliability oversight."
    on_disk = _read_disk(fake_repo)["business_area"]
    assert any(e["id"] == "ops" for e in on_disk)
    events = _persona_events(in_memory_store)
    assert len(events) == 1
    assert events[0]["payload"]["persona_id"] == "ops"
    assert events[0]["payload"]["prev_version"] == 0
    assert events[0]["payload"]["next_version"] == 1


# ---------------------------------------------------------------------------
# Axis 2: POST duplicate id without Idempotency-Key → 409 persona_already_exists
# ---------------------------------------------------------------------------


def test_post_duplicate_id_returns_409(client: TestClient) -> None:
    body = {"entry": {"id": "commerce", "display_name": "Commerce dup"}}
    r = client.post("/v1/personas/business_area", json=body, headers=ADMIN_HEADERS)
    assert r.status_code == 409
    assert r.json()["code"] == "persona_already_exists"


# ---------------------------------------------------------------------------
# Axis 3: POST with Idempotency-Key replays prior request (returns 201, no double event)
# ---------------------------------------------------------------------------


def test_post_idempotency_key_replays_without_double_event(
    client: TestClient,
    in_memory_store: InMemoryEventStore,
) -> None:
    idem = str(uuid4())
    body = {"entry": {"id": "ops", "display_name": "Ops"}}
    r1 = client.post(
        "/v1/personas/business_area",
        json=body,
        headers={**ADMIN_HEADERS, "Idempotency-Key": idem},
    )
    assert r1.status_code == 201
    r2 = client.post(
        "/v1/personas/business_area",
        json=body,
        headers={**ADMIN_HEADERS, "Idempotency-Key": idem},
    )
    assert r2.status_code == 201
    assert len(_persona_events(in_memory_store)) == 1


# ---------------------------------------------------------------------------
# Axis 4: POST 422 length-cap (instructions > 8000 chars)
# ---------------------------------------------------------------------------


def test_post_instructions_length_cap_returns_422(client: TestClient) -> None:
    body = {
        "entry": {
            "id": "huge",
            "instructions": "x" * (PERSONA_INSTRUCTIONS_MAX_CHARS + 1),
        },
    }
    r = client.post("/v1/personas/business_area", json=body, headers=ADMIN_HEADERS)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Axis 5: PATCH happy path increments version, sets new instructions
# ---------------------------------------------------------------------------


def test_patch_updates_field_and_increments_version(
    client: TestClient,
    fake_repo: Path,
    in_memory_store: InMemoryEventStore,
) -> None:
    body = {"expected_version": 1, "instructions": "New brief.", "actor": "alice"}
    r = client.patch(
        "/v1/personas/business_area/commerce", json=body, headers=ADMIN_HEADERS,
    )
    assert r.status_code == 200, r.text
    entry = next(e for e in r.json()["business_area"] if e["id"] == "commerce")
    assert entry["instructions"] == "New brief."
    assert entry["version"] == 2
    on_disk = _read_disk(fake_repo)
    assert next(e for e in on_disk["business_area"] if e["id"] == "commerce")["version"] == 2
    events = _persona_events(in_memory_store)
    assert events[-1]["payload"]["fields_changed"] == ["instructions"]


# ---------------------------------------------------------------------------
# Axis 6: PATCH 409 on version skew
# ---------------------------------------------------------------------------


def test_patch_version_conflict_returns_409(client: TestClient) -> None:
    body = {"expected_version": 99, "instructions": "wrong version"}
    r = client.patch(
        "/v1/personas/business_area/commerce", json=body, headers=ADMIN_HEADERS,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "persona_version_conflict"


# ---------------------------------------------------------------------------
# Axis 7: PATCH 422 length-cap (instructions > 8000 chars)
# ---------------------------------------------------------------------------


def test_patch_length_cap_returns_422(client: TestClient) -> None:
    body = {
        "expected_version": 1,
        "instructions": "x" * (PERSONA_INSTRUCTIONS_MAX_CHARS + 1),
    }
    r = client.patch(
        "/v1/personas/business_area/commerce", json=body, headers=ADMIN_HEADERS,
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Axis 8: PATCH 422 when body sets no mutable fields (empty patch)
# ---------------------------------------------------------------------------


def test_patch_empty_body_returns_422(client: TestClient) -> None:
    body = {"expected_version": 1, "actor": "alice"}
    r = client.patch(
        "/v1/personas/business_area/commerce", json=body, headers=ADMIN_HEADERS,
    )
    assert r.status_code == 422
    assert r.json()["code"] == "empty_patch"


# ---------------------------------------------------------------------------
# Axis 9: PUT happy path replaces full entry and increments version
# ---------------------------------------------------------------------------


def test_put_replaces_entry_and_increments_version(
    client: TestClient, in_memory_store: InMemoryEventStore,
) -> None:
    body = {
        "entry": {
            "id": "commerce",
            "display_name": "Commerce 2",
            "instructions": "Refreshed.",
        },
        "expected_version": 1,
    }
    r = client.put(
        "/v1/personas/business_area/commerce", json=body, headers=ADMIN_HEADERS,
    )
    assert r.status_code == 200, r.text
    entry = next(e for e in r.json()["business_area"] if e["id"] == "commerce")
    assert entry["display_name"] == "Commerce 2"
    assert entry["version"] == 2
    assert _persona_events(in_memory_store)[-1]["payload"]["next_version"] == 2


# ---------------------------------------------------------------------------
# Axis 10: PUT 404 when persona does not exist
# ---------------------------------------------------------------------------


def test_put_unknown_persona_returns_404(client: TestClient) -> None:
    body = {"entry": {"id": "ghost", "display_name": "Ghost"}, "expected_version": 0}
    r = client.put(
        "/v1/personas/business_area/ghost", json=body, headers=ADMIN_HEADERS,
    )
    assert r.status_code == 404
    assert r.json()["code"] == "persona_not_found"


# ---------------------------------------------------------------------------
# Axis 11: DELETE happy + 409 version skew
# ---------------------------------------------------------------------------


def test_delete_removes_persona_and_emits_audit(
    client: TestClient, fake_repo: Path, in_memory_store: InMemoryEventStore,
) -> None:
    r = client.delete(
        "/v1/personas/business_area/commerce",
        params={"expected_version": 1, "actor": "alice"},
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 204
    on_disk = _read_disk(fake_repo)["business_area"]
    assert not any(e["id"] == "commerce" for e in on_disk)
    assert _persona_events(in_memory_store)[-1]["payload"]["fields_changed"] == ["__deleted__"]


def test_delete_version_conflict_returns_409(client: TestClient) -> None:
    r = client.delete(
        "/v1/personas/business_area/commerce",
        params={"expected_version": 99},
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# Axis 12: unknown shelf → 422
# ---------------------------------------------------------------------------


def test_post_unknown_shelf_returns_422(client: TestClient) -> None:
    r = client.post(
        "/v1/personas/archived",
        json={"entry": {"id": "ops", "display_name": "Ops"}},
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 422
    assert r.json()["code"] == "invalid_shelf"


# ---------------------------------------------------------------------------
# Axis 13: reserved persona_id → 422
# ---------------------------------------------------------------------------


def test_post_reserved_persona_id_returns_422(client: TestClient) -> None:
    r = client.post(
        "/v1/personas/business_area",
        json={"entry": {"id": "default", "display_name": "Default"}},
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 422
    assert r.json()["code"] == "reserved_persona_id"


# ---------------------------------------------------------------------------
# Axis 14: read-after-write via GET /v1/personas
# ---------------------------------------------------------------------------


def test_read_after_write_shows_updated_catalog(client: TestClient) -> None:
    body = {"expected_version": 1, "instructions": "Brief A."}
    client.patch(
        "/v1/personas/business_area/commerce", json=body, headers=ADMIN_HEADERS,
    )
    r = client.get("/v1/personas")
    assert r.status_code == 200
    entry = next(e for e in r.json()["business_area"] if e["id"] == "commerce")
    assert entry["instructions"] == "Brief A."
    assert entry["version"] == 2


# ---------------------------------------------------------------------------
# Bonus: 401 on missing admin token (sanity that gate is wired)
# ---------------------------------------------------------------------------


def test_post_without_admin_token_returns_401(client: TestClient) -> None:
    r = client.post(
        "/v1/personas/business_area",
        json={"entry": {"id": "ops", "display_name": "Ops"}},
    )
    assert r.status_code == 401
