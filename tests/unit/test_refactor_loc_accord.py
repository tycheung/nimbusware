from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.loc_accord_stage import (
    REFACTOR_LOC_ACCORD_STAGE,
    emit_refactor_loc_accord_stage,
    evaluate_loc_accord,
)
from orchestrator.refactor_stage import emit_refactor_stage_and_critique
from orchestrator.registry import RoleRegistry
from orchestrator.workflow_refactor import RefactorWorkflowBlock
from store.memory import InMemoryEventStore

_REPO = Path(__file__).resolve().parents[2]


def test_evaluate_loc_accord_budget() -> None:
    assert evaluate_loc_accord(100) is True
    assert evaluate_loc_accord(500) is False


def test_emit_refactor_loc_accord_stage_events() -> None:
    store = InMemoryEventStore()
    run_id = uuid4()
    passed = emit_refactor_loc_accord_stage(store, run_id, loc_delta=50)
    assert passed is True
    stages = [
        (r.get("payload") or {}).get("stage_name")
        for r in store.list_run_events(str(run_id))
        if r.get("event_type") == "stage.started"
    ]
    assert REFACTOR_LOC_ACCORD_STAGE in stages


def test_refactor_stage_emits_loc_accord_metadata(tmp_path: Path) -> None:
    ws = tmp_path / "proj"
    ws.mkdir()
    for idx in range(20):
        (ws / f"module_{idx}.py").write_text("x = 1\n" * 30, encoding="utf-8")
    store = InMemoryEventStore()
    registry = RoleRegistry.from_yaml(_REPO / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(
        _REPO / "configs" / "personas" / "critique_pairings.yaml",
    )
    run_id = uuid4()
    failed = emit_refactor_stage_and_critique(
        store,
        registry,
        router,
        run_id=run_id,
        block=RefactorWorkflowBlock(enabled=True),
        workspace=ws,
    )
    assert failed is False
    rows = store.list_run_events(str(run_id))
    loc_accord_stages = [
        (r.get("payload") or {}).get("stage_name")
        for r in rows
        if r.get("event_type") == "stage.started"
    ]
    assert REFACTOR_LOC_ACCORD_STAGE in loc_accord_stages
    refactor_started = next(
        r for r in rows if (r.get("payload") or {}).get("stage_name") == "refactor"
    )
    refactor = (refactor_started.get("metadata") or {}).get("refactor") or {}
    assert refactor.get("loc_total", 0) > 0
    assert "loc_accord" in refactor
