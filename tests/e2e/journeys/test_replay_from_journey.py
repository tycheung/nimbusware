from __future__ import annotations

import pytest

from e2e.harness.journey import JourneyClient

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey]


def test_replay_from_checkpoint_via_api(journey_client: JourneyClient) -> None:
    client = journey_client.client
    create = client.post("/v1/runs", json={"workflow_profile": "default"})
    assert create.status_code in (200, 201)
    run_id = create.json()["run_id"]
    denied = client.post(
        f"/v1/runs/{run_id}/replay-from",
        json={"from_store_seq": 0, "operator_ack": False},
    )
    assert denied.status_code == 422
    ok = client.post(
        f"/v1/runs/{run_id}/replay-from",
        json={"from_store_seq": 0, "operator_ack": True, "reason": "e2e journey"},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body.get("replay_started") is True
