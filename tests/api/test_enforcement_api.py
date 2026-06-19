from __future__ import annotations

from fastapi.testclient import TestClient


def test_enforcement_preset_endpoint(client: TestClient) -> None:
    resp = client.get("/v1/enforcement/presets/10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["level"] == 10
    assert body["terminal_parity_ci"] is True


def test_run_enforcement_put_get(client: TestClient) -> None:
    create = client.post(
        "/v1/runs",
        json={"workflow_profile": "micro_slice", "requirements": {"business_prompt": "test"}},
    )
    assert create.status_code == 200
    run_id = create.json()["run_id"]
    put = client.put(
        f"/v1/runs/{run_id}/enforcement",
        json={"level": 7},
    )
    assert put.status_code == 200, put.text
    assert put.json()["level"] == 7
    assert put.json()["security_mode"] == "full_scan"
    get = client.get(f"/v1/runs/{run_id}/enforcement")
    assert get.status_code == 200
    assert get.json()["level"] == 7


def test_run_created_includes_enforcement_effective(client: TestClient) -> None:
    create = client.post(
        "/v1/runs",
        json={
            "workflow_profile": "patch",
            "work_type": "patch",
            "requirements": {"business_prompt": "fix"},
        },
    )
    assert create.status_code == 200
    run_id = create.json()["run_id"]
    store = client.app.state.store
    rows = store.list_run_events(str(run_id))
    created = next(r for r in rows if r.get("event_type") == "run.created")
    eff = (created.get("metadata") or {}).get("enforcement_effective") or {}
    assert eff.get("level") == 4
