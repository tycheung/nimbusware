from __future__ import annotations

from fastapi.testclient import TestClient

from env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

_ADMIN = {"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN}


def test_probation_reliability_not_found(client: TestClient) -> None:
    r = client.get(
        "/v1/personas/business_area/does-not-exist/probation-reliability",
        headers=_ADMIN,
    )
    assert r.status_code == 404
