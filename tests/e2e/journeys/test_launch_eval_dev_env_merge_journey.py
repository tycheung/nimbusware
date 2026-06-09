from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from agent_core.models import EventType, StagePassedEvent, StagePassedPayload
from e2e.harness.journey import JourneyClient
from e2e.harness.workspace import copy_fixture_repo
from nimbusware_orchestrator.launch_evaluator import (
    evaluate_workspace_rubric,
    merge_dev_env_into_scorecard,
)

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey]


def test_launch_eval_merges_dev_env_regression_from_run_events(
    journey_client: JourneyClient,
    tmp_path: Path,
) -> None:
    ws = copy_fixture_repo("tiny_python_app", tmp_path / "launch-dev-env-ws")
    journey_client.attach_project(ws)
    journey_client.start_micro_slice_run(business_prompt="Launch eval dev-env merge")
    run_id = UUID(str(journey_client.run_id))
    store = journey_client.client.app.state.store

    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"dev_env": {"regression": "ok"}},
            payload=StagePassedPayload(stage_name="dev_env.regression.passed", duration_ms=0),
        ),
    )
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "dev_env": {
                    "ui_regression": "button missing",
                    "flow_id": "tiny_web_smoke",
                    "failed_step": 3,
                    "locator": "role=button:Add",
                }
            },
            payload=StagePassedPayload(stage_name="dev_env.ui_regression.failed", duration_ms=0),
        ),
    )

    scored = journey_client.client.post(f"/v1/runs/{run_id}/maker/launch-eval")
    assert scored.status_code == 200, scored.text
    body = scored.json()
    assert body.get("dev_env_http_regression_passed") is True
    assert body.get("dev_env_ui_regression_passed") is False
    assert body.get("dev_env_live_regression_passed") is False
    assert body.get("put_ui_flow_id") == "tiny_web_smoke"
    assert body.get("dev_env_ui_failed_step") == 3
    assert body.get("passed") is False

    rows = store.list_run_events(str(run_id))
    base = evaluate_workspace_rubric(ws, min_aggregate=0.0)
    merged = merge_dev_env_into_scorecard(base, rows)
    assert merged.dev_env_live_regression_passed is False
