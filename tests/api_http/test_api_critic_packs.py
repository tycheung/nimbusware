from __future__ import annotations

from fastapi.testclient import TestClient

from env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

_ADMIN = {"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN}


def test_list_critic_packs(client: TestClient) -> None:
    r = client.get("/v1/config/critic-packs", headers=_ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert "pack_ids" in body
    assert isinstance(body["pack_ids"], list)
    assert body.get("count", 0) >= 0


def test_get_critic_pack_not_found(client: TestClient) -> None:
    r = client.get("/v1/config/critic-packs/does-not-exist-pack", headers=_ADMIN)
    assert r.status_code == 404


def test_get_default_security_pack(client: TestClient) -> None:
    listed = client.get("/v1/config/critic-packs", headers=_ADMIN).json()
    ids = listed.get("pack_ids") or []
    if "default-security" not in ids:
        return
    r = client.get("/v1/config/critic-packs/default-security", headers=_ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["pack_id"] == "default-security"
    assert body["content"].get("domain") == "security"


def test_critic_pack_workflows_endpoint(client: TestClient) -> None:
    listed = client.get("/v1/config/critic-packs", headers=_ADMIN).json()
    ids = listed.get("pack_ids") or []
    if not ids:
        return
    pack_id = ids[0]
    r = client.get(f"/v1/config/critic-packs/{pack_id}/workflows", headers=_ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["pack_id"] == pack_id
    assert "workflow_profiles" in body
    assert isinstance(body["workflow_profiles"], list)


def test_put_critic_pack_without_postgres(client: TestClient) -> None:
    r = client.put(
        "/v1/config/critic-packs/test-pack",
        headers=_ADMIN,
        json={"domain": "security", "blocking_authority": "advisory"},
    )
    assert r.status_code in (503, 200)
