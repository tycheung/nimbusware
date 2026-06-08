from __future__ import annotations

from pathlib import Path

import pytest

from e2e.harness.journey import JourneyClient
from e2e.harness.workspace import copy_fixture_repo

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey]


def test_interjection_queue_next_before_last_via_api(
    journey_client: JourneyClient,
    tmp_path: Path,
) -> None:
    ws = copy_fixture_repo("tiny_python_app", tmp_path / "interjection-ws")
    journey_client.attach_project(ws)
    journey_client.start_micro_slice_run(business_prompt="Interjection queue ordering")
    run_id = journey_client.run_id
    assert run_id

    last = journey_client.client.post(
        f"/v1/runs/{run_id}/interjection-queue",
        json={"message": "last task", "priority": "last"},
    )
    assert last.status_code == 200, last.text
    nxt = journey_client.client.post(
        f"/v1/runs/{run_id}/interjection-queue",
        json={"message": "next task", "priority": "next"},
    )
    assert nxt.status_code == 200, nxt.text

    body = journey_client.client.get(f"/v1/runs/{run_id}/interjection-queue")
    assert body.status_code == 200, body.text
    items = body.json().get("queue", {}).get("items") or []
    assert len(items) == 2
    assert items[0]["message"] == "next task"
    assert items[0]["priority"] == "next"
