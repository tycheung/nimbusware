from __future__ import annotations

import pytest

from console.enterprise_console import (
    build_enterprise_headers,
    enterprise_console_feature_enabled,
    fleet_memory_status_table_rows,
    fleet_sli_aggregate_caption,
    fleet_worker_health_caption,
    is_enterprise_edition_manifest,
    register_tenant_api_key,
    resolve_active_api_key,
    tenant_select_options,
)
from iam.constants import API_KEY_HEADER


def test_build_enterprise_headers() -> None:
    assert build_enterprise_headers("secret") == {API_KEY_HEADER: "secret"}
    assert build_enterprise_headers("") == {}


def test_enterprise_console_feature_gate() -> None:
    manifest = {
        "edition": "enterprise",
        "features": {"enterprise_console": {"status": "enabled"}},
    }
    assert is_enterprise_edition_manifest(manifest)
    assert enterprise_console_feature_enabled(manifest)
    individual = {
        "edition": "individual",
        "features": {"enterprise_console": {"status": "enabled"}},
    }
    assert not enterprise_console_feature_enabled(individual)


def test_tenant_select_options() -> None:
    opts = tenant_select_options(
        {
            "tenants": [
                {"slug": "ops", "display_name": "Operations"},
                {"slug": "acme", "display_name": "Acme"},
            ],
        },
    )
    slugs = [s for s, _ in opts]
    assert slugs == ["acme", "ops"]
    assert opts[1][0] == "ops"


def test_resolve_active_api_key_prefers_tenant_map() -> None:
    key = resolve_active_api_key(
        primary_key="primary",
        tenant_keys={"ops": "ops-secret"},
        selected_tenant_slug="ops",
    )
    assert key == "ops-secret"


def test_register_tenant_api_key() -> None:
    out = register_tenant_api_key({}, tenant_slug="ops", api_key="k1")
    assert out["ops"] == "k1"


def test_fleet_memory_status_table_rows() -> None:
    rows = fleet_memory_status_table_rows(
        {
            "tenant_id": "t1",
            "local_chunk_count": 3,
            "remote": {"configured": True},
        },
    )
    assert any(r["field"] == "local_chunk_count" and r["value"] == 3 for r in rows)


def test_fleet_sli_aggregate_caption() -> None:
    cap = fleet_sli_aggregate_caption(
        {
            "fleet_sli": {
                "sustained_export_present": True,
                "sustained_p95_latency_ms": 120,
                "combined_max_p95_latency_ms": 200,
            },
            "preflight_history": {
                "runs_with_preflight": 2,
                "preflight_coverage_ratio": 1.0,
            },
        },
    )
    assert cap is not None
    assert "sustained_p95_ms=120" in cap
    assert "Preflight history SLI" in cap


def test_fleet_worker_health_caption() -> None:
    cap = fleet_worker_health_caption(
        {"ok": True, "backpressure": "ok", "metrics": {"queue": {"pending": 1}}},
    )
    assert cap is not None
    assert "backpressure=ok" in cap


def test_fetch_platform_edition_uses_client(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_get_json(path: str, *, timeout: float = 15.0, **kwargs: object) -> dict[str, str]:
        captured["path"] = path
        captured["timeout"] = timeout
        captured["kwargs"] = kwargs
        return {"edition": "enterprise"}

    monkeypatch.setattr(
        "console.services.enterprise.get_json",
        _fake_get_json,
    )
    from console.enterprise_console import fetch_platform_edition

    body = fetch_platform_edition(timeout=12.0)
    assert body["edition"] == "enterprise"
    assert captured["path"] == "/platform/edition"
    assert captured["timeout"] == 12.0


def test_enterprise_fleet_dashboard_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_EDITION", "enterprise")
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "test-admin-secret")
    from fastapi.testclient import TestClient

    from api.app import app
    from iam.constants import API_KEY_HEADER

    with TestClient(app) as client:
        boot = client.post(
            "/v1/enterprise/iam/bootstrap",
            headers={"X-Nimbusware-Admin-Token": "test-admin-secret"},
        )
        headers = {API_KEY_HEADER: boot.json()["api_key"]}
        me = client.get("/v1/enterprise/iam/me", headers=headers)
        assert me.status_code == 200
        tenants = client.get("/v1/enterprise/tenants", headers=headers)
        assert tenants.status_code == 200
        assert len(tenants.json()["tenants"]) >= 1
