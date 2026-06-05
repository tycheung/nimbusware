from __future__ import annotations

from fastapi.testclient import TestClient


def test_compare_run_policies(client: TestClient) -> None:
    a = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    b = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    r = client.get("/v1/policy/compare", params={"run_a": a, "run_b": b})
    assert r.status_code == 200
    body = r.json()
    assert body["run_a"] == a
    assert body["run_b"] == b
    assert "identical" in body
    assert "changed" in body


def test_compare_run_policies_404_missing_run(client: TestClient) -> None:
    a = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    r = client.get(
        "/v1/policy/compare",
        params={"run_a": a, "run_b": "00000000-0000-4000-8000-000000000099"},
    )
    assert r.status_code == 404


def test_audit_export(client: TestClient) -> None:
    rid = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    r = client.get(f"/v1/runs/{rid}/audit-export")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/gzip")
    assert len(r.content) > 20
