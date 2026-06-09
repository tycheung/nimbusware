from __future__ import annotations

import pytest

from e2e.harness.journey import JourneyClient
from e2e.harness.timeline import assert_timeline_golden, load_golden_timeline
from e2e.harness.workspace import copy_fixture_repo

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey, pytest.mark.e2e_fixture_repo]


def test_campaign_micro_slice_created_timeline(
    journey_client: JourneyClient,
    tmp_path,
) -> None:
    ws = copy_fixture_repo("tiny_python_app", tmp_path / "campaign-golden")
    journey_client.attach_project(ws)
    resp = journey_client.client.post(
        "/v1/campaigns",
        json={
            "project_id": journey_client.project_id,
            "requirements": {"business_prompt": "Campaign golden timeline"},
            "autonomous": False,
            "workflow_profile": "campaign_micro_slice",
        },
        headers=journey_client.admin_headers,
    )
    assert resp.status_code == 200, resp.text
    journey_client.run_id = str(resp.json()["run_id"])
    golden = load_golden_timeline("campaign_micro_slice_created.json")
    assert_timeline_golden(journey_client.timeline(), golden)


def test_micro_slice_web_created_timeline(
    journey_client: JourneyClient,
    tmp_path,
) -> None:
    ws = copy_fixture_repo("tiny_web_app", tmp_path / "web-golden")
    journey_client.attach_project(ws)
    journey_client.start_run("micro_slice_web", business_prompt="Web profile golden timeline")
    golden = load_golden_timeline("micro_slice_web_created.json")
    assert_timeline_golden(journey_client.timeline(), golden)


def test_micro_slice_fullstack_created_timeline(
    journey_client: JourneyClient,
    tmp_path,
) -> None:
    ws = copy_fixture_repo("tiny_todo_fullstack", tmp_path / "fullstack-golden")
    journey_client.attach_project(ws)
    journey_client.start_run(
        "micro_slice_fullstack",
        business_prompt="Fullstack profile golden timeline",
    )
    golden = load_golden_timeline("micro_slice_fullstack_created.json")
    assert_timeline_golden(journey_client.timeline(), golden)


def test_campaign_factory_zero_touch_created_timeline(
    journey_client: JourneyClient,
    tmp_path,
) -> None:
    ws = copy_fixture_repo("tiny_api_app", tmp_path / "factory-golden")
    journey_client.attach_project(ws)
    resp = journey_client.client.post(
        "/v1/campaigns",
        json={
            "project_id": journey_client.project_id,
            "requirements": {"business_prompt": "Factory zero-touch golden timeline"},
            "autonomous": False,
            "workflow_profile": "campaign_factory_zero_touch",
        },
        headers=journey_client.admin_headers,
    )
    assert resp.status_code == 200, resp.text
    journey_client.run_id = str(resp.json()["run_id"])
    golden = load_golden_timeline("campaign_factory_zero_touch_created.json")
    assert_timeline_golden(journey_client.timeline(), golden)
