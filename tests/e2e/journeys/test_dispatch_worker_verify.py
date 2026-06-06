"""Dispatch worker smoke with memory dispatch mode."""

from __future__ import annotations

import pytest

from e2e.harness.journey import JourneyClient

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_stack]


def test_default_run_with_memory_dispatch(
    journey_client: JourneyClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_RUN_DISPATCH", "memory")
    journey_client.start_default_run()
    journey_client.wait_for_event("run.created")
