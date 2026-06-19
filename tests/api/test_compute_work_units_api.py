from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from nimbusware_api.app import app
from nimbusware_compute.work_unit import get_work_unit_queue


def test_claim_and_complete_work_unit_round_trip() -> None:
    client = TestClient(app)
    queue = get_work_unit_queue()
    run_id = uuid4()
    session_id = uuid4()
    node_id = uuid4()
    enqueued = queue.enqueue(
        run_id=run_id,
        stage_name="slice.verify",
        session_id=session_id,
        agent_role="backend_writer",
        payload={"mesh_assignment": True},
    )
    depth = client.get(f"/v1/compute/work-units/queue?session_id={session_id}")
    assert depth.status_code == 200
    assert depth.json()["queued"] >= 1

    claim = client.post(
        "/v1/compute/work-units/claim",
        json={"node_id": str(node_id), "session_id": str(session_id)},
    )
    assert claim.status_code == 200
    unit = claim.json()["work_unit"]
    assert unit is not None
    assert unit["work_unit_id"] == str(enqueued.work_unit_id)
    assert unit["status"] == "assigned"

    complete = client.post(
        f"/v1/compute/work-units/{enqueued.work_unit_id}/complete",
        json={"status": "ok", "result": {"mesh_ack": True}},
    )
    assert complete.status_code == 200
    assert complete.json()["work_unit"]["status"] == "ok"

    claim_empty = client.post(
        "/v1/compute/work-units/claim",
        json={"node_id": str(node_id), "session_id": str(session_id)},
    )
    assert claim_empty.json()["work_unit"] is None
