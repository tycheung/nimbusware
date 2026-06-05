from __future__ import annotations

from fastapi.testclient import TestClient

from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

_ADMIN = {"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN}


def test_config_blast_radius_requires_profile(client: TestClient) -> None:
    r = client.get("/v1/config/blast-radius", headers=_ADMIN)
    assert r.status_code == 422


def test_config_blast_radius_returns_shape(client: TestClient) -> None:
    r = client.get(
        "/v1/config/blast-radius",
        params={"workflow_profile": "micro_slice", "run_limit": 10},
        headers=_ADMIN,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["workflow_profile"] == "micro_slice"
    assert "proposed_effective" in body
    assert "affected_run_count" in body
    assert isinstance(body.get("affected_runs"), list)
