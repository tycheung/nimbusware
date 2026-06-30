from __future__ import annotations

import os
from uuid import uuid4

from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

ADMIN_HEADERS = {
    "X-Nimbusware-Admin-Token": os.environ.get(
        "NIMBUSWARE_ADMIN_TOKEN",
        DEFAULT_NIMBUSWARE_ADMIN_TOKEN,
    ),
}


def test_admin_ui_timeline_panels_404(client: TestClient) -> None:
    rid = str(uuid4())
    r = client.get(
        f"/v1/admin/ui/runs/{rid}/timeline-panels",
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 404


def test_admin_ui_timeline_panels_after_create(client: TestClient, tmp_path) -> None:
    ws = tmp_path / "panels-app"
    ws.mkdir()
    project = client.post(
        "/v1/projects",
        json={"name": "Panels", "workspace_path": str(ws), "template": "attach"},
        headers=ADMIN_HEADERS,
    ).json()
    run = client.post(
        "/v1/runs",
        json={
            "workflow_profile": "micro_slice",
            "project_id": project["project_id"],
            "requirements": {"business_prompt": "hello"},
        },
        headers=ADMIN_HEADERS,
    ).json()
    run_id = run["run_id"]
    r = client.get(
        f"/v1/admin/ui/runs/{run_id}/timeline-panels",
        headers=ADMIN_HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == run_id
    for key in (
        "integrator_gate",
        "agent_evaluator",
        "self_refinement",
        "run_escalated",
        "security_scan_on_verify",
        "universal_critique",
    ):
        assert key in body
