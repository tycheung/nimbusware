from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from nimbusware_api.app import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_deploy_ci_poll_skips_without_github_repo(client: TestClient) -> None:
    created = client.post("/v1/runs", json={"workflow_profile": "default"})
    assert created.status_code == 200, created.text
    run_id = created.json()["run_id"]
    resp = client.post("/v1/platform/deploy/ci-poll", json={"run_id": run_id})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "skipped"


def test_deploy_ci_poll_emits_timeline_event(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = client.post("/v1/runs", json={"workflow_profile": "default"})
    run_id = created.json()["run_id"]
    monkeypatch.setattr(
        "nimbusware_api.routes.platform_deploy_mutations.maker_user_id_str",
        lambda _req: "test-user",
    )
    monkeypatch.setattr(
        "nimbusware_api.routes.platform_deploy_mutations.load_deploy_credentials",
        lambda *_a, **_k: {
            "github_repo": "acme/app",
            "workflow_path": ".github/workflows/nimbusware-ci.yaml",
        },
    )
    monkeypatch.setattr(
        "nimbusware_api.routes.platform_deploy_mutations.poll_github_workflow_run",
        lambda **_k: {
            "status": "passed",
            "detail": "Nimbusware CI · completed · success",
            "run_url": "https://github.com/acme/app/actions/runs/9",
        },
    )
    resp = client.post("/v1/platform/deploy/ci-poll", json={"run_id": run_id})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "passed"
    timeline = client.get(f"/v1/runs/{run_id}/timeline?limit=20")
    events = timeline.json().get("events") or []
    assert any(ev.get("payload", {}).get("stage_name") == "ci.workflow" for ev in events)
