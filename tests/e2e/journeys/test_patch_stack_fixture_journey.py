from __future__ import annotations

from pathlib import Path

import pytest

from e2e.harness.journey import JourneyClient
from e2e.harness.workspace import copy_fixture_repo

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_fixture_repo]


@pytest.mark.parametrize(
    ("fixture_name", "profile"),
    [
        ("tiny_go_app", "patch_go"),
        ("tiny_jvm_app", "patch_jvm"),
    ],
)
def test_patch_stack_fixture_attach_and_run_created(
    journey_client: JourneyClient,
    tmp_path: Path,
    fixture_name: str,
    profile: str,
) -> None:
    ws = copy_fixture_repo(fixture_name, tmp_path / fixture_name)
    journey_client.attach_project(ws, name=f"PatchStack-{fixture_name}")
    body = journey_client.start_run(profile, business_prompt=f"Fix failing test in {fixture_name}")
    assert body.get("run_id")
    run = journey_client.client.get(f"/v1/runs/{journey_client.run_id}")
    assert run.status_code == 200
    detail = run.json()
    assert detail.get("workflow_profile") == profile
