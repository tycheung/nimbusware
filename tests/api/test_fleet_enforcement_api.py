from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from nimbusware_env.edition import ENTERPRISE_EDITION, ENV_EDITION
from nimbusware_iam.constants import API_KEY_HEADER


def test_tenant_enforcement_policy_put_get(monkeypatch: pytest.MonkeyPatch) -> None:
    slug = f"enf-{uuid4().hex[:8]}"
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "test-admin-secret")
    from nimbusware_api.app import app

    with TestClient(app) as client:
        boot = client.post(
            "/v1/enterprise/iam/bootstrap",
            headers={"X-Nimbusware-Admin-Token": "test-admin-secret"},
        )
        assert boot.status_code == 200
        admin_headers = {API_KEY_HEADER: boot.json()["api_key"]}

        created = client.post(
            "/v1/enterprise/tenants",
            headers=admin_headers,
            json={"slug": slug, "display_name": "Enforcement"},
        )
        assert created.status_code == 200
        tenant_id = created.json()["tenant_id"]

        get_resp = client.get(
            f"/v1/enterprise/tenants/{tenant_id}/enforcement-policy",
            headers=admin_headers,
        )
        assert get_resp.status_code == 200
        assert 0 <= get_resp.json()["max_enforcement_level"] <= 10

        put_resp = client.put(
            f"/v1/enterprise/tenants/{tenant_id}/enforcement-policy",
            headers=admin_headers,
            json={"min_enforcement_level": 5, "max_enforcement_level": 9},
        )
        assert put_resp.status_code == 200, put_resp.text
        body = put_resp.json()
        assert body["min_enforcement_level"] == 5
        assert body["max_enforcement_level"] == 9

        get2 = client.get(
            f"/v1/enterprise/tenants/{slug}/enforcement-policy",
            headers=admin_headers,
        )
        assert get2.status_code == 200
        assert get2.json()["min_enforcement_level"] == 5


def test_admin_bff_fleet_enforcement_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "test-admin-secret")
    from nimbusware_api.app import app

    with TestClient(app) as client:
        boot = client.post(
            "/v1/enterprise/iam/bootstrap",
            headers={"X-Nimbusware-Admin-Token": "test-admin-secret"},
        )
        admin_headers = {API_KEY_HEADER: boot.json()["api_key"]}
        created = client.post(
            "/v1/enterprise/tenants",
            headers=admin_headers,
            json={"slug": "bff-enf", "display_name": "BFF"},
        )
        tenant_id = created.json()["tenant_id"]
        q = f"?tenant_id={tenant_id}"
        put = client.put(
            f"/v1/admin/ui/enterprise/fleet-enforcement-policy{q}",
            headers=admin_headers,
            json={"min_enforcement_level": 4, "max_enforcement_level": 8},
        )
        assert put.status_code == 200, put.text
        get = client.get(
            f"/v1/admin/ui/enterprise/fleet-enforcement-policy{q}",
            headers=admin_headers,
        )
        assert get.status_code == 200
        assert get.json()["max_enforcement_level"] == 8
