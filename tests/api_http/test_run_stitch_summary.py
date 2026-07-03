from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


def test_run_stitch_summary_empty_for_new_run(client: TestClient, tmp_path: Path) -> None:
    ws = tmp_path / "stitch-ws"
    ws.mkdir()
    project = client.post(
        "/v1/projects",
        json={"name": "stitch", "workspace_path": str(ws), "template": "attach"},
    ).json()
    run = client.post(
        "/v1/runs",
        json={
            "project_id": project["project_id"],
            "workflow_profile": "micro_slice",
            "requirements": {"business_prompt": "demo"},
        },
    ).json()
    run_id = run["run_id"]
    res = client.get(f"/v1/runs/{run_id}/stitch-summary")
    assert res.status_code == 200
    body = res.json()
    assert body["run_id"] == run_id
    assert body["events"] == []
