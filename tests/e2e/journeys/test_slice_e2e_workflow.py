from __future__ import annotations

from pathlib import Path

import pytest

from e2e.harness.journey import JourneyClient
from e2e.harness.timeline import load_golden_timeline
from e2e.harness.workspace import copy_fixture_repo

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.e2e_journey,
    pytest.mark.e2e_fixture_repo,
    pytest.mark.slice_e2e,
]


def test_micro_slice_web_profile_loads() -> None:
    from nimbusware_env import find_repo_root
    from nimbusware_orchestrator.workflow_profiles import workflow_profile_dict

    repo = find_repo_root()
    profile = workflow_profile_dict(repo, "micro_slice_web")
    assert profile.get("slice", {}).get("e2e", {}).get("enabled") is True


def test_tiny_web_app_fixture_copy(tmp_path: Path) -> None:
    ws = copy_fixture_repo("tiny_web_app", tmp_path / "web-ws")
    assert (ws / "index.html").is_file()


def _stub_orchestrator_modules(ws: Path) -> None:
    target_dir = ws / "packages/nimbusware_orchestrator"
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "micro_slice.py").write_text("# stub\n", encoding="utf-8")
    (target_dir / "slice_gate.py").write_text("# stub\n", encoding="utf-8")


def test_micro_slice_web_apply_emits_slice_e2e_stage(
    journey_client: JourneyClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_SLICE_E2E_COMMAND", "python -c \"print('ok')\"")
    ws = copy_fixture_repo("tiny_web_app", tmp_path / "web-ws")
    _stub_orchestrator_modules(ws)

    journey_client.attach_project(ws)
    journey_client.start_run("micro_slice_web")
    journey_client.approve_plan()
    prep = journey_client.prepare_slice()
    assert prep["status"] == "awaiting_approval"
    slice_id = prep["pending"]["slice_id"]

    applied = journey_client.apply_slice(slice_id)
    assert applied["status"] == "applied"

    stage_names = [
        (ev.get("payload") or {}).get("stage_name")
        for ev in journey_client.timeline()
        if ev.get("event_type") in ("stage.started", "stage.passed")
    ]
    assert "slice.e2e" in stage_names

    golden = load_golden_timeline("micro_slice_web_apply.json")
    from e2e.harness.timeline import assert_timeline_golden

    assert_timeline_golden(journey_client.timeline(), golden)
