from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from e2e.harness.journey import JourneyClient
from e2e.harness.stack import start_inprocess_dispatch_worker
from e2e.harness.workspace import copy_fixture_repo
from nimbusware_api.app import app

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.e2e_journey,
    pytest.mark.e2e_fixture_repo,
    pytest.mark.e2e_stack,
]


def _prepare_tiny_api_workspace(tmp_path: Path) -> Path:
    ws = copy_fixture_repo("tiny_api_app", tmp_path / "api-campaign")
    orch_dir = ws / "packages" / "nimbusware_orchestrator"
    orch_dir.mkdir(parents=True, exist_ok=True)
    (orch_dir / "micro_slice.py").write_text("# api campaign stub\n", encoding="utf-8")
    (orch_dir / "slice_gate.py").write_text("# gate stub\n", encoding="utf-8")
    return ws


def test_tiny_api_campaign_dispatch_worker_generates_backlog(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_RUN_DISPATCH", "memory")
    ws = _prepare_tiny_api_workspace(tmp_path)
    with TestClient(app) as client:
        queue = app.state.run_queue
        assert queue is not None
        worker = start_inprocess_dispatch_worker(app.state.orchestrator, queue)
        try:
            jc = JourneyClient(client=client)
            jc.attach_project(ws, name="TinyApiCampaign")
            resp = client.post(
                "/v1/campaigns",
                json={
                    "project_id": jc.project_id,
                    "requirements": {"business_prompt": "REST contacts API campaign"},
                    "autonomous": True,
                    "workflow_profile": "campaign_micro_slice",
                },
                headers=jc.admin_headers,
            )
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body.get("dispatch_mode") == "queued"
            run_id = str(body["run_id"])
            deadline = time.monotonic() + 60.0
            saw_backlog = False
            while time.monotonic() < deadline:
                timeline = client.get(f"/v1/runs/{run_id}/timeline")
                assert timeline.status_code == 200, timeline.text
                types = {e.get("event_type") for e in timeline.json().get("events", [])}
                if "delivery_backlog.generated" in types or "slice.queued" in types:
                    saw_backlog = True
                    break
                time.sleep(0.25)
            assert saw_backlog
            assert (ws / "src" / "app" / "routes.py").is_file()
        finally:
            worker.join()
