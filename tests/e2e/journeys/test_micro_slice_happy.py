from __future__ import annotations

from pathlib import Path

import pytest

from e2e.harness.journey import JourneyClient
from e2e.harness.timeline import assert_timeline_golden, load_golden_timeline
from e2e.harness.workspace import copy_fixture_repo

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey]


@pytest.mark.e2e_fixture_repo
def test_micro_slice_happy_apply(
    journey_client: JourneyClient,
    tmp_path: Path,
) -> None:
    ws = copy_fixture_repo("tiny_python_app", tmp_path / "ws")
    (ws / "packages/orchestrator").mkdir(parents=True, exist_ok=True)
    (ws / "packages/orchestrator/micro_slice.py").write_text(
        "# stub\n", encoding="utf-8"
    )
    (ws / "packages/orchestrator/slice_gate.py").write_text("# stub\n", encoding="utf-8")

    journey_client.attach_project(ws)
    journey_client.start_micro_slice_run()
    assert journey_client.get_pending()["plan_approved"] is False

    journey_client.approve_plan()
    prep = journey_client.prepare_slice()
    assert prep["status"] == "awaiting_approval"
    slice_id = prep["pending"]["slice_id"]

    applied = journey_client.apply_slice(slice_id)
    assert applied["status"] == "applied"
    assert applied.get("gate_passed") is True

    golden = load_golden_timeline("micro_slice_happy.json")
    assert_timeline_golden(journey_client.timeline(), golden)


def test_micro_slice_skip_after_plan(
    journey_client: JourneyClient,
    tmp_path: Path,
) -> None:
    ws = tmp_path / "skip-ws"
    ws.mkdir()
    (ws / "packages/orchestrator").mkdir(parents=True)
    (ws / "packages/orchestrator/micro_slice.py").write_text("# x\n", encoding="utf-8")
    (ws / "packages/orchestrator/slice_gate.py").write_text("# y\n", encoding="utf-8")

    journey_client.attach_project(ws)
    journey_client.start_micro_slice_run()
    journey_client.approve_plan()

    lifecycle = journey_client.lifecycle_slice()
    assert lifecycle["status"] in {"awaiting_approval", "all_slices_done"}
    if lifecycle.get("status") == "awaiting_approval":
        slice_id = lifecycle["pending"]["slice_id"]
        skipped = journey_client.skip_slice(slice_id)
        assert skipped["status"] == "skipped"


def test_micro_slice_revert_after_apply(
    journey_client: JourneyClient,
    tmp_path: Path,
) -> None:
    ws = tmp_path / "revert-ws"
    ws.mkdir()
    target_dir = ws / "packages/orchestrator"
    target_dir.mkdir(parents=True)
    target = target_dir / "micro_slice.py"
    target.write_text("# before\n", encoding="utf-8")
    (target_dir / "slice_gate.py").write_text("# y\n", encoding="utf-8")

    journey_client.attach_project(ws)
    journey_client.start_micro_slice_run()
    journey_client.approve_plan()
    prep = journey_client.prepare_slice()
    if prep.get("status") != "awaiting_approval":
        pytest.skip("no pending slice in this environment")
    slice_id = prep["pending"]["slice_id"]
    before = target.read_text(encoding="utf-8")

    assert journey_client.apply_slice(slice_id)["status"] == "applied"
    target.write_text("corrupted\n", encoding="utf-8")
    reverted = journey_client.revert_workspace()
    assert reverted["status"] == "reverted"
    assert target.read_text(encoding="utf-8") == before
