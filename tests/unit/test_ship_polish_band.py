from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from agent_core.models import EventType, StagePassedEvent, StagePassedPayload
from nimbusware_orchestrator.diagnose_learn import write_learning_doc
from nimbusware_orchestrator.learnings_catalog import list_workspace_learnings
from nimbusware_orchestrator.user_autopilot_profiles import (
    load_user_autopilot_profiles,
    upsert_user_autopilot_profile,
)
from nimbusware_projections.builders.run_theater import build_run_theater_messages


def test_theater_resolution_and_improvement_council_lines() -> None:
    run_id = uuid4()
    rows = [
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={
                "resolution_council": {
                    "detail": "accord_fix_slice",
                    "accord": True,
                    "rounds": 2,
                    "dissent": ["minor lint"],
                },
            },
            payload=StagePassedPayload(stage_name="resolution.council", duration_ms=0),
        ).model_dump(mode="json"),
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            metadata={"improvement_council": {"selected": "simplify"}},
            payload=StagePassedPayload(stage_name="improvement.council", duration_ms=0),
        ).model_dump(mode="json"),
    ]
    for i, row in enumerate(rows, start=1):
        row["store_seq"] = i
    msgs = build_run_theater_messages(rows)
    assert any(m.get("data_testid") == "theater-resolution-council" for m in msgs)
    assert any(m.get("data_testid") == "theater-improvement-council" for m in msgs)


def test_list_workspace_learnings(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    write_learning_doc(
        ws,
        title="Missing import",
        body="Add httpx to requirements",
        fingerprint="abc123def4567890",
    )
    items = list_workspace_learnings(ws)
    assert len(items) == 1
    assert items[0]["title"] == "Missing import"


def test_user_autopilot_profiles_roundtrip(tmp_path: Path) -> None:
    upsert_user_autopilot_profile(
        profile_id="ship_fast",
        name="Ship fast",
        level=8,
        checkpoints=["stop_on_gate_fail"],
        repo_root=tmp_path,
    )
    profiles = load_user_autopilot_profiles(tmp_path)
    assert "ship_fast" in profiles
    assert profiles["ship_fast"].level == 8
