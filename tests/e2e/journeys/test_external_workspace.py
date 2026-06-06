from __future__ import annotations

from pathlib import Path

import pytest

from e2e.harness.journey import JourneyClient
from e2e.harness.workspace import copy_fixture_repo

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_fixture_repo]


def test_external_fixture_workspace_attach(
    journey_client: JourneyClient,
    tmp_path: Path,
) -> None:
    ws = copy_fixture_repo("tiny_python_app", tmp_path / "external-ws")
    journey_client.attach_project(ws, name="ExternalFixture")
    journey_client.start_micro_slice_run(business_prompt="Calculator app")
    pending = journey_client.get_pending()
    assert pending["plan_approved"] is False
    assert journey_client.project_id
    assert journey_client.workspace_path == ws.resolve()
