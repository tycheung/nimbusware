from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import app
from e2e.harness.journey import JourneyClient
from e2e.harness.stack import start_inprocess_dispatch_worker

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_stack]

_FIXTURE_WS = Path(__file__).resolve().parents[2] / "fixtures" / "repos" / "tiny_python_app"


def test_campaign_queued_dispatch_worker_generates_backlog(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_RUN_DISPATCH", "memory")
    with TestClient(app) as client:
        queue = app.state.run_queue
        assert queue is not None
        worker = start_inprocess_dispatch_worker(app.state.orchestrator, queue)
        try:
            jc = JourneyClient(client=client)
            jc.attach_project(_FIXTURE_WS, name="dispatch-worker-journey")
            resp = client.post(
                "/v1/campaigns",
                json={
                    "project_id": jc.project_id,
                    "requirements": {"business_prompt": "dispatch worker stack"},
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
        finally:
            worker.join()
