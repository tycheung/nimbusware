from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from agent_core.models import EventType, RunCreatedEvent, RunCreatedPayload
from orchestrator.factory_cadence import launch_eval_completed
from orchestrator.launch_evaluator import maybe_run_launch_eval_for_campaign
from orchestrator.maintenance_refactor import run_maintenance_refactor
from store.memory import InMemoryEventStore

REPO = Path(__file__).resolve().parents[2]


class _MaintenanceOrch:
    def __init__(self, store: InMemoryEventStore, repo_root: Path) -> None:
        self._store = store
        self._repo_root = repo_root

    @property
    def repo_root(self) -> Path:
        return self._repo_root


def test_maintenance_pass_emits_launch_eval_rubric_on_fixture() -> None:
    store = InMemoryEventStore()
    ws = REPO / "tests" / "fixtures" / "repos" / "tiny_python_app"
    run_id = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            metadata={
                "project": {
                    "id": str(uuid4()),
                    "name": "maintenance-rubric",
                    "workspace_path": str(ws),
                    "template": "attach",
                },
                "campaign_effective": {
                    "enabled": True,
                    "completion": {
                        "factory_tier": "T0",
                        "auto_launch_eval": True,
                    },
                },
            },
            payload=RunCreatedPayload(
                workflow_profile="campaign_micro_slice",
                policy_version="1",
                config_snapshot_id="snap",
            ),
        ),
    )
    orch = _MaintenanceOrch(store, REPO)
    run_maintenance_refactor(orch, run_id, slices_completed=3, insert_fix_slices=False)
    rows = store.list_run_events(str(run_id))
    assert launch_eval_completed(rows)


def test_maybe_run_launch_eval_for_campaign_scores_tiny_python() -> None:
    store = InMemoryEventStore()
    ws = REPO / "tests" / "fixtures" / "repos" / "tiny_python_app"
    run_id = uuid4()
    store.append(
        RunCreatedEvent(
            event_type=EventType.RUN_CREATED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            metadata={
                "project": {
                    "id": str(uuid4()),
                    "name": "launch-rubric",
                    "workspace_path": str(ws),
                    "template": "attach",
                },
            },
            payload=RunCreatedPayload(
                workflow_profile="micro_slice",
                policy_version="1",
                config_snapshot_id="snap",
            ),
        ),
    )
    rows = store.list_run_events(str(run_id))
    scorecard = maybe_run_launch_eval_for_campaign(store, run_id, rows, workspace=ws)
    assert scorecard is not None
    assert scorecard.aggregate >= 0.0
    assert launch_eval_completed(store.list_run_events(str(run_id)))
