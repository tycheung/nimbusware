from __future__ import annotations

from fastapi.testclient import TestClient


def test_override_gate_appends_event(client: TestClient) -> None:
    rid = client.post("/v1/runs", json={"workflow_profile": "default"}).json()["run_id"]
    r = client.post(
        f"/v1/runs/{rid}/actions/override-gate",
        json={
            "actor_id": "human:test",
            "reason_code": "manual_review",
            "stage_name": "slice.gate",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "gate_overridden"
    tl = client.get(f"/v1/runs/{rid}/timeline").json()
    assert tl.get("gate_overridden") is not None
    assert tl["gate_overridden"]["stage_name"] == "slice.gate"


def test_override_gate_run_not_found(client: TestClient) -> None:
    r = client.post(
        "/v1/runs/00000000-0000-4000-8000-000000000099/actions/override-gate",
        json={
            "actor_id": "a",
            "reason_code": "b",
            "stage_name": "plan",
        },
    )
    assert r.status_code == 404
