from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from agent_core.models import EventType
from api.routes.enterprise import fleet_memory as fm
from api.routes.memory_chunks import list_memory_chunks
from api.routes.runs import memory_insert as mi
from env.edition import ENTERPRISE_EDITION, ENV_EDITION
from iam.constants import DEFAULT_TENANT_ID
from iam.context import reset_auth_context, set_auth_context
from iam.models import AuthContext


def _auth(tenant_id) -> AuthContext:
    return AuthContext(
        tenant_id=tenant_id,
        tenant_slug="t",
        key_id=uuid4(),
        role_taxonomy_keys=(),
        api_scopes=("maker_admin",),
    )


@pytest.fixture(autouse=True)
def _reset_ctx() -> None:
    yield
    reset_auth_context()


def test_search_under_memory_1_broker_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak493-i: search returns broker_miss body under MEMORY=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    with patch("api.routes.enterprise.fleet_memory.try_broker_memory_search", return_value=None):
        out = fm.fleet_memory_search(
            _gate=object(),  # type: ignore[arg-type]
            q="widget auth",
        )
    assert out.get("via") == "broker_miss"
    assert out.get("feature") == "fleet_memory_search"
    assert out.get("status") == "degraded"
    assert out.get("hits") == []
    assert out.get("query") == "widget auth"


def test_search_under_memory_1_broker_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak493-i: search returns broker hits under MEMORY=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    with patch(
        "api.routes.enterprise.fleet_memory.try_broker_memory_search",
        return_value={"hits": [{"id": "m1", "text": "note"}]},
    ):
        out = fm.fleet_memory_search(
            _gate=object(),  # type: ignore[arg-type]
            q="widget auth",
            k=3,
        )
    assert out.get("via") == "broker"
    assert out.get("hit_count") == 1
    assert out["hits"][0]["id"] == "m1"


def test_search_under_memory_2_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak493-i: search maps broker failure to 503 under MEMORY=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "2")
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    with (
        patch(
            "api.routes.enterprise.fleet_memory.try_broker_memory_search",
            side_effect=RuntimeError("broker down"),
        ),
        pytest.raises(HTTPException) as ei,
    ):
        fm.fleet_memory_search(
            _gate=object(),  # type: ignore[arg-type]
            q="widget auth",
        )
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_memory_only"


def test_status_under_memory_1_broker_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak493-i: status returns broker_miss body under MEMORY=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    with patch("api.routes.enterprise.fleet_memory.try_broker_memory_search", return_value=None):
        out = fm.fleet_memory_status(_gate=object())  # type: ignore[arg-type]
    assert out.get("via") == "broker_miss"
    assert out.get("feature") == "fleet_memory_status"
    assert out.get("status") == "degraded"
    assert out.get("local_chunk_count") == 0


def test_status_under_memory_1_broker_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak493-i: status probe succeeds under MEMORY=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    with patch(
        "api.routes.enterprise.fleet_memory.try_broker_memory_search",
        return_value={"hits": [{"id": "m1"}]},
    ):
        out = fm.fleet_memory_status(_gate=object())  # type: ignore[arg-type]
    assert out.get("via") == "broker"
    assert out.get("local_chunk_count") == 1
    assert out.get("remote", {}).get("via") == "broker"


def test_rebuild_under_memory_1_broker_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak494-b: rebuild returns broker_miss under MEMORY=1 (no local peel_index)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    with patch("api.routes.enterprise.fleet_memory.rebuild_fleet_memory_index") as rebuild:
        out = fm.fleet_memory_rebuild(
            fm.FleetRebuildBody(org_slug="default"),
            _gate=object(),  # type: ignore[arg-type]
            store=object(),
        )
    rebuild.assert_not_called()
    assert out.get("via") == "broker_miss"
    assert out.get("feature") == "fleet_memory_rebuild"
    assert out.get("status") == "degraded"
    assert out.get("org_scope_hash") is not None


def test_rebuild_under_memory_2_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak494-b: rebuild maps to 503 under MEMORY=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "2")
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    with (
        patch("api.routes.enterprise.fleet_memory.rebuild_fleet_memory_index") as rebuild,
        pytest.raises(HTTPException) as ei,
    ):
        fm.fleet_memory_rebuild(
            fm.FleetRebuildBody(org_slug="default"),
            _gate=object(),  # type: ignore[arg-type]
            store=object(),
        )
    rebuild.assert_not_called()
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_memory_only"


def test_sync_under_memory_1_broker_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak494-b: sync returns broker_miss under MEMORY=1 (no local peel_index)."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    with patch("api.routes.enterprise.fleet_memory.push_fleet_memory_to_canonical") as push:
        out = fm.fleet_memory_sync(
            fm.FleetSyncBody(org_slug="default", direction="push"),
            _gate=object(),  # type: ignore[arg-type]
        )
    push.assert_not_called()
    assert out.get("via") == "broker_miss"
    assert out.get("feature") == "fleet_memory_sync"
    assert out.get("status") == "degraded"
    assert out.get("direction") == "push"


def test_sync_under_memory_2_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak494-b: sync maps to 503 under MEMORY=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "2")
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    with (
        patch("api.routes.enterprise.fleet_memory.pull_fleet_memory_from_canonical") as pull,
        pytest.raises(HTTPException) as ei,
    ):
        fm.fleet_memory_sync(
            fm.FleetSyncBody(org_slug="default", direction="pull"),
            _gate=object(),  # type: ignore[arg-type]
        )
    pull.assert_not_called()
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_memory_only"


def test_status_under_memory_2_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak493-i: status maps broker failure to 503 under MEMORY=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "2")
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    set_auth_context(_auth(DEFAULT_TENANT_ID))
    with (
        patch(
            "api.routes.enterprise.fleet_memory.try_broker_memory_search",
            side_effect=RuntimeError("status down"),
        ),
        pytest.raises(HTTPException) as ei,
    ):
        fm.fleet_memory_status(_gate=object())  # type: ignore[arg-type]
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_memory_only"


def test_chunks_list_under_memory_1_broker_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-b: GET /memory/chunks returns broker_miss under MEMORY=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    project_id = uuid4()
    record = MagicMock(workspace_path="/tmp/ws")
    store = MagicMock()
    store.get.return_value = record
    with (
        patch("api.routes.memory_chunks.repo_scope_hash", return_value="scope-hash"),
        patch("api.routes.memory_chunks.require_local_memory_chunk_store") as guard,
    ):
        guard.return_value = {
            "via": "broker_miss",
            "feature": "memory_chunks_list",
            "status": "degraded",
            "chunks": [],
            "total": 0,
        }
        out = list_memory_chunks(
            project_id=project_id,
            store=store,
            _user=object(),  # type: ignore[arg-type]
            limit=100,
        )
    assert out.get("via") == "broker_miss"
    assert out.get("feature") == "memory_chunks_list"
    assert out.get("chunks") == []


def test_chunks_list_under_memory_2_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-b: GET /memory/chunks maps to 503 under MEMORY=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "2")
    project_id = uuid4()
    record = MagicMock(workspace_path="/tmp/ws")
    store = MagicMock()
    store.get.return_value = record
    with (
        patch("api.routes.memory_chunks.repo_scope_hash", return_value="scope-hash"),
        pytest.raises(HTTPException) as ei,
    ):
        list_memory_chunks(
            project_id=project_id,
            store=store,
            _user=object(),  # type: ignore[arg-type]
            limit=100,
        )
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_memory_only"


def test_insert_under_memory_1_broker_miss(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-b: POST memory-chunk insert returns broker_miss under MEMORY=1."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "1")
    run_id = uuid4()
    chunk_id = uuid4()
    project_id = uuid4()
    store = MagicMock()
    store.list_run_events.return_value = [
        {
            "event_type": EventType.RUN_CREATED.value,
            "metadata": {"project": {"project_id": str(project_id)}},
        },
    ]
    project = MagicMock(workspace_path="/tmp/ws")
    project_store = MagicMock()
    project_store.get.return_value = project
    with (
        patch("api.routes.runs.memory_insert.repo_scope_hash", return_value="scope-hash"),
        patch("api.routes.runs.memory_insert.require_local_memory_chunk_store") as guard,
    ):
        guard.return_value = {
            "via": "broker_miss",
            "feature": "memory_chunk_insert",
            "status": "degraded",
            "run_id": str(run_id),
            "chunk_id": str(chunk_id),
        }
        out = mi.post_insert_memory_chunk(
            run_id=run_id,
            chunk_id=chunk_id,
            store=store,
            project_store=project_store,
            _orch=object(),  # type: ignore[arg-type]
        )
    assert out.get("via") == "broker_miss"
    assert out.get("feature") == "memory_chunk_insert"


def test_insert_under_memory_2_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """sak498-b: POST memory-chunk insert maps to 503 under MEMORY=2."""
    monkeypatch.setenv("NIMBUSWARE_BROKER_MEMORY", "2")
    run_id = uuid4()
    chunk_id = uuid4()
    project_id = uuid4()
    store = MagicMock()
    store.list_run_events.return_value = [
        {
            "event_type": EventType.RUN_CREATED.value,
            "metadata": {"project": {"project_id": str(project_id)}},
        },
    ]
    project = MagicMock(workspace_path="/tmp/ws")
    project_store = MagicMock()
    project_store.get.return_value = project
    with (
        patch("api.routes.runs.memory_insert.repo_scope_hash", return_value="scope-hash"),
        pytest.raises(HTTPException) as ei,
    ):
        mi.post_insert_memory_chunk(
            run_id=run_id,
            chunk_id=chunk_id,
            store=store,
            project_store=project_store,
            _orch=object(),  # type: ignore[arg-type]
        )
    assert ei.value.status_code == 503
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "broker_memory_only"
