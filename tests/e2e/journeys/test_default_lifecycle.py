from __future__ import annotations

import pytest

from e2e.harness.journey import JourneyClient
from e2e.harness.timeline import assert_timeline_golden, load_golden_timeline

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey]


def test_default_run_created_timeline(journey_client: JourneyClient) -> None:
    journey_client.start_default_run()
    journey_client.wait_for_event("run.created")
    golden = load_golden_timeline("default_lifecycle.json")
    assert_timeline_golden(journey_client.timeline(), golden)
