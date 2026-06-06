from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nimbusware_env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN

ADMIN_HEADERS = {"X-Nimbusware-Admin-Token": DEFAULT_NIMBUSWARE_ADMIN_TOKEN}

pytestmark = pytest.mark.slow


def test_maker_progress_404(client: TestClient) -> None:
    r = client.get("/v1/runs/00000000-0000-4000-8000-000000009999/maker-progress")
    assert r.status_code == 404


def test_maker_progress_after_intent_run(client: TestClient, tmp_path: Path) -> None:
    ws = tmp_path / "intent-app"
    ws.mkdir()
    project = client.post(
        "/v1/projects",
        json={"name": "Intent", "workspace_path": str(ws), "template": "attach"},
        headers=ADMIN_HEADERS,
    ).json()
    run = client.post(
        "/v1/runs",
        json={
            "workflow_profile": "micro_slice",
            "project_id": project["project_id"],
            "requirements": {
                "business_prompt": "Small inventory tracker",
                "clarifications": [
                    {
                        "question_id": "audience",
                        "question": "Who?",
                        "answer": "Shop owner",
                    },
                ],
            },
        },
    )
    assert run.status_code == 200
    run_id = run.json()["run_id"]
    progress = client.get(f"/v1/runs/{run_id}/maker-progress")
    assert progress.status_code == 200
    body = progress.json()
    assert "inventory tracker" in body["plan_summary"].lower()
    assert body["status"] == "awaiting_plan"
    assert body["simple_mode"] is True


def test_maker_progress_includes_campaign_progress(
    client: TestClient,
) -> None:
    fixture_ws = Path(__file__).resolve().parents[2] / "fixtures" / "repos" / "tiny_python_app"
    project = client.post(
        "/v1/projects",
        json={
            "name": "CampaignProgress",
            "workspace_path": str(fixture_ws),
            "template": "attach",
        },
        headers=ADMIN_HEADERS,
    )
    assert project.status_code == 200
    campaign = client.post(
        "/v1/campaigns",
        json={
            "project_id": project.json()["project_id"],
            "requirements": {"business_prompt": "Campaign maker progress"},
            "autonomous": True,
            "workflow_profile": "campaign_micro_slice",
        },
        headers=ADMIN_HEADERS,
    )
    assert campaign.status_code == 200
    run_id = campaign.json()["run_id"]
    progress = client.get(f"/v1/runs/{run_id}/maker-progress?simple=true")
    assert progress.status_code == 200
    body = progress.json()
    assert body.get("campaign_progress", {}).get("state") in {
        "executing",
        "paused",
        "completed",
        "failed",
    }
