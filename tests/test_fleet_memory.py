"""Enterprise fleet memory (fo202)."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from agent_core.models import EventType
from hermes_memory.fleet_index import rebuild_fleet_memory_index
from hermes_memory.fleet_sync import pull_fleet_memory_from_canonical, push_fleet_memory_to_canonical
from hermes_memory.org_scope import (
    fleet_scope_hash,
    memory_namespace_for_repo,
    require_fleet_memory_feature,
    resolve_fleet_scope,
)
from hermes_memory.remote_store import FileFleetMemoryCanonicalStore
from hermes_memory.search import search_fleet_memory
from hermes_memory.store import InMemoryMemoryChunkStore
from hermes_memory.sync_cli import main as sync_cli_main
from nimbusware_env.edition import DEFAULT_EDITION, ENTERPRISE_EDITION, ENV_EDITION
from nimbusware_iam.context import set_auth_context
from nimbusware_iam.models import AuthContext
from nimbusware_iam.store import InMemoryIamStore


def _sample_rows(run_id: UUID | None = None) -> list[dict]:
    rid = run_id or uuid4()
    return [
        {
            "store_seq": 1,
            "run_id": rid,
            "event_type": EventType.RUN_CREATED.value,
            "metadata": {},
            "payload": {},
        },
        {
            "store_seq": 2,
            "run_id": rid,
            "event_type": EventType.FINDING_CREATED.value,
            "payload": {
                "finding_id": str(uuid4()),
                "category": "sql_injection",
                "severity": "critical",
            },
        },
    ]


def test_individual_rejects_fleet_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, DEFAULT_EDITION)
    with pytest.raises(RuntimeError, match="Enterprise edition required"):
        require_fleet_memory_feature()


def test_fleet_scope_hash_stable() -> None:
    tenant = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    assert fleet_scope_hash(tenant) == fleet_scope_hash(tenant)
    assert fleet_scope_hash(tenant) != fleet_scope_hash(tenant, org_slug="other")


def test_repo_namespace_equals_repo_scope() -> None:
    assert memory_namespace_for_repo("abc123") == "abc123"


def test_fleet_memory_tenant_isolation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    iam = InMemoryIamStore()
    tenant_a = iam.create_tenant(slug="a", display_name="A")
    tenant_b = iam.create_tenant(slug="b", display_name="B")
    ctx_a = iam.verify_api_key(iam.create_api_key(tenant_id=tenant_a.tenant_id).api_key)
    ctx_b = iam.verify_api_key(iam.create_api_key(tenant_id=tenant_b.tenant_id).api_key)
    assert ctx_a is not None and ctx_b is not None

    mem = InMemoryMemoryChunkStore()
    set_auth_context(ctx_a)
    rebuild_fleet_memory_index(
        mem,
        repo_root=tmp_path,
        tenant_id=ctx_a.tenant_id,
        in_memory_event_rows=_sample_rows(),
    )
    set_auth_context(ctx_b)
    rebuild_fleet_memory_index(
        mem,
        repo_root=tmp_path,
        tenant_id=ctx_b.tenant_id,
        in_memory_event_rows=_sample_rows(),
    )

    scope_a = fleet_scope_hash(ctx_a.tenant_id)
    scope_b = fleet_scope_hash(ctx_b.tenant_id)
    assert len(mem.list_chunks_for_org_scope(scope_a, tenant_id=ctx_a.tenant_id)) >= 1
    assert mem.list_chunks_for_org_scope(scope_b, tenant_id=ctx_a.tenant_id) == []

    set_auth_context(ctx_a)
    hits_a = search_fleet_memory(
        mem,
        "sql injection",
        org_scope_hash=scope_a,
        tenant_id=ctx_a.tenant_id,
        repo_root=tmp_path,
    )
    assert hits_a
    set_auth_context(ctx_b)
    assert (
        search_fleet_memory(
            mem,
            "sql injection",
            org_scope_hash=scope_a,
            tenant_id=ctx_b.tenant_id,
            repo_root=tmp_path,
        )
        == []
    )


def test_fleet_memory_pull_push_roundtrip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    tenant_id = uuid4()
    _, org_scope = resolve_fleet_scope(tenant_id=tenant_id)
    mem = InMemoryMemoryChunkStore()
    rebuild_fleet_memory_index(
        mem,
        repo_root=tmp_path,
        tenant_id=tenant_id,
        in_memory_event_rows=_sample_rows(),
    )
    canonical = tmp_path / "canonical"
    pushed = push_fleet_memory_to_canonical(
        mem,
        canonical_root=canonical,
        tenant_id=tenant_id,
    )
    assert pushed["chunk_count"] >= 1

    fresh = InMemoryMemoryChunkStore()
    pulled = pull_fleet_memory_from_canonical(
        fresh,
        canonical_root=canonical,
        tenant_id=tenant_id,
    )
    assert pulled["generation_id"] == pushed["generation_id"]
    assert len(fresh.list_chunks_for_org_scope(org_scope, tenant_id=tenant_id)) >= 1

    store = FileFleetMemoryCanonicalStore(canonical)
    assert store.list_generations(org_scope)


def test_sync_cli_rejects_individual(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, DEFAULT_EDITION)
    rc = sync_cli_main(["pull"])
    assert rc == 2


def test_enterprise_fleet_memory_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "test-admin-secret")
    from fastapi.testclient import TestClient
    from nimbusware_api.app import app
    from nimbusware_iam.constants import API_KEY_HEADER

    with TestClient(app) as client:
        boot = client.post(
            "/v1/enterprise/iam/bootstrap",
            headers={"X-Nimbusware-Admin-Token": "test-admin-secret"},
        )
        headers = {API_KEY_HEADER: boot.json()["api_key"]}

        status = client.get("/v1/enterprise/fleet-memory/status", headers=headers)
        assert status.status_code == 200
        assert status.json()["fleet_memory_enabled"] is True

        rebuild = client.post(
            "/v1/enterprise/fleet-memory/rebuild",
            headers=headers,
            json={"org_slug": "default"},
        )
        assert rebuild.status_code == 200
        assert rebuild.json()["chunks_added"] >= 0

        search = client.get(
            "/v1/enterprise/fleet-memory/search",
            headers=headers,
            params={"q": "sql"},
        )
        assert search.status_code == 200
