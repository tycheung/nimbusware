from __future__ import annotations

from pathlib import Path

import pytest

from e2e.harness.journey import JourneyClient
from e2e.harness.workspace import copy_fixture_repo

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey]


def test_factory_zero_touch_profile_loads(journey_client: JourneyClient, tmp_path: Path) -> None:
    ws = copy_fixture_repo("tiny_api_app", tmp_path / "factory-ws")
    journey_client.attach_project(ws)
    journey_client.start_run(
        "campaign_factory_zero_touch",
        business_prompt="Build a contacts REST API with health endpoint",
    )
    assert journey_client.run_id
    progress = journey_client.client.get(f"/v1/runs/{journey_client.run_id}/maker-progress")
    assert progress.status_code == 200, progress.text
    body = progress.json()
    assert body.get("campaign_progress") is not None or body.get("run_id")
